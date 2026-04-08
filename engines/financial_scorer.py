"""
Financial Scorer Engine
Post-processes the clustered GeoDataFrame to calculate CAPEX, Energy Yield,
and LCOE metrics based on user-configurable reference data.
Matches the logic from the Excel reference file (GES/RES sheets).
"""
import pandas as pd
import numpy as np
import logging

class FinancialScorer:
    """
    Extends the ClusterScorer output with Financial and Energy metrics.
    """

    @classmethod
    def calculate_financials(cls, cluster_gdf, financial_constants, cp_values=None, project_type="Solar"):
        """
        Main entry point for financial calculations.
        
        Parameters
        ----------
        cluster_gdf : GeoDataFrame
            Output of ClusterScorer (one row per cluster with connection distances/types).
        financial_constants : dict
            Dictionary containing base CAPEX rates, transmission config, etc.
        cp_values : list[dict]
            List of CP lookup values for Wind mode.
        project_type : str
            "Solar", "OnShore", or "OffShore".
            
        Returns
        -------
        GeoDataFrame with CAPEX, Energy, and LCOE columns added.
        """
        logging.info(f"FinancialScorer: calculating financials for {len(cluster_gdf)} clusters ({project_type})")
        df = cluster_gdf.copy()
        
        # Ensure base columns exist
        if "Installed_Capacity_MW" not in df.columns:
            logging.warning("Installed_Capacity_MW missing for financials.")
            return df
            
        capacity = df["Installed_Capacity_MW"]
        
        # ── 1. Common Line CAPEX Calculation ─────────────────────────────
        # Excel: Uses a matrix of capacity ranges and connection distances
        df["LİNE CAPEX"] = cls._calculate_line_capex(df, financial_constants)
        
        df["line expropriation"] = df["LİNE CAPEX"] * financial_constants.get("line_expropriation_ratio", 0.1)

        # ── 2. Project Type Specifics ────────────────────────────────────
        if project_type == "Solar":
            # Solar CAPEX Breakdown
            base_capex = capacity * financial_constants.get("pv_capex_per_mw", 500000)
            df["CAPEX OF PV"] = base_capex
            df["SUBSTATION COST"] = base_capex * financial_constants.get("substation_pv_ratio", 0.08)
            df["LAND COST"] = base_capex * financial_constants.get("land_cost_ratio", 0.1)
            
            # Slope Cost: (CAPEX * Slope * 9/15) / 100
            slope_vals = df["Mean_Slope_mean"] if "Mean_Slope_mean" in df.columns else pd.Series(0.0, index=df.index)
            df["SLOPE COST"] = (base_capex * slope_vals.fillna(0) * (9/15)) / 100
            
            # TOTAL CAPEX = LİNE + PV + SUBSTATION + LINE EXPROP + SLOPE + LAND
            df["TOTAL CAPEX"] = (df["LİNE CAPEX"] + df["CAPEX OF PV"] + df["SUBSTATION COST"] + 
                                 df["line expropriation"] + df["SLOPE COST"] + df["LAND COST"])
            
            # Solar Energy Yield — Series-safe column access
            solar_irrad = df["Solar_irradiation_rate"] if "Solar_irradiation_rate" in df.columns else pd.Series(0.0, index=df.index)
            temp        = df["Mean_Temperature_mean"]  if "Mean_Temperature_mean"  in df.columns else pd.Series(0.0, index=df.index)
            slope       = df["Mean_Slope_mean"]        if "Mean_Slope_mean"        in df.columns else pd.Series(0.0, index=df.index)
            if solar_irrad.isna().all() or (solar_irrad == 0).all():
                logging.warning("Solar_irradiation_rate column missing or all zeros — Yearly energy will be 0.")
            # Solar_irradiation_rate can be absolute (e.g. kWh/m² 1400-2000) or already 0-100.
            # Normalize to 0–1 fraction by dividing by max so that 1688 multiplier makes sense.
            irrad_max = solar_irrad.max()
            if pd.notna(irrad_max) and irrad_max > 1:
                solar_irrad_frac = solar_irrad / irrad_max
            else:
                solar_irrad_frac = solar_irrad
            # Formula: (1688 * irrad_frac * Cap) ± temperature correction
            base_yield = 1688 * solar_irrad_frac * capacity
            temp_loss = 0.004 * base_yield * (0 - temp.fillna(0))
            df["Yearly energy(MWh)"] = base_yield + temp_loss
            
            # Capacity Factor
            df["Capacity Factor"] = df["Yearly energy(MWh)"] / (8760 * capacity)
            
        else:
            # Wind CAPEX Breakdown
            base_capex = capacity * financial_constants.get("wind_capex_per_mw", 1000000)
            df["CAPEX"] = base_capex
            df["substation"] = base_capex * financial_constants.get("substation_wind_ratio", 0.06)
            df["land cost"] = base_capex * financial_constants.get("land_cost_ratio", 0.1)

            # Transport Networks: Mean_Transport_Total × 400,000 + (MW/4) × 2,000
            transport_dist = df["Mean_Transport_Total"] if "Mean_Transport_Total" in df.columns else pd.Series(0.0, index=df.index)
            df["TRANSPORT NETWORKS"] = transport_dist * 400000 + (capacity / 4) * 2000

            # TOTAL CAPEX
            df["TOTAL CAPEX"] = (df["LİNE CAPEX"] + df["CAPEX"] + df["substation"] +
                                 df["TRANSPORT NETWORKS"] + df["line expropriation"] + df["land cost"])

            # LINE CAPEX RATE: (LINE_CAPEX + line_exp) / (CAPEX + sub + TRANSPORT + land) × 100
            denom = df["CAPEX"] + df["substation"] + df["TRANSPORT NETWORKS"] + df["land cost"]
            df["LİNE CAPEX RATE"] = ((df["LİNE CAPEX"] + df["line expropriation"]) / denom.replace(0, np.nan)) * 100

            # Wind Energy Yield — use Series-safe column access to avoid scalar-0 silent bug
            wind_speed = df["Mean_Wind_mean"] if "Mean_Wind_mean" in df.columns else pd.Series(0.0, index=df.index)
            altitude   = df["Mean_Altitude"]   if "Mean_Altitude"   in df.columns else pd.Series(0.0, index=df.index)
            if wind_speed.isna().all() or (wind_speed == 0).all():
                logging.warning("Mean_Wind_mean column missing or all zeros — Yearly energy will be 0.")

            df["CP"] = cls._lookup_cp_values(wind_speed.fillna(0), cp_values)

            # Air density: 1.225 − 0.264 × (altitude / 2000)
            air_density = 1.225 - 0.264 * (altitude.fillna(0) / 2000)
            # Swept area for 69 m rotor radius: π × 69²
            swept_area = 3.14 * 69 * 69
            # ENERJİ = ((0.5 × ρ × A × v³ × CP) × 8760 / 1 000 000) × MW / 4.2
            raw_yield = (0.5 * air_density * swept_area * (wind_speed.fillna(0) ** 3) * df["CP"] * 8760) / 1_000_000
            df["Yearly energy(MWh)"] = raw_yield * (capacity / 4.2)

            # Capacity Factor
            df["Capacity Factor"] = df["Yearly energy(MWh)"] / (8760 * capacity)

        # Override Capacity Factor if user specified a fixed value
        user_cf = financial_constants.get("capacity_factor")
        if user_cf is not None and user_cf > 0:
            df["Capacity Factor"] = float(user_cf)
            df["Yearly energy(MWh)"] = float(user_cf) * 8760 * capacity

        # ── 3. General Financial Metrics ─────────────────────────────────
        df["CAPEX/MW($)"] = df["TOTAL CAPEX"] / capacity
        
        # Score with Capacity Factor
        max_cf = df["Capacity Factor"].max()
        if max_cf and max_cf > 0:
            df["Scaled_Overall_Score"] = df.get("Overall_Score", 0) * (df["Capacity Factor"] / max_cf)
        else:
            df["Scaled_Overall_Score"] = df.get("Overall_Score", 0)
            
        # Simplified LCOE - assuming standard operational cost
        opex_percentage = 0.02 # 2% of CAPEX roughly
        lifetime = 25
        discount_rate = 0.08
        
        # LCOE = (Capex + sum_t(Opex_t/(1+r)^t)) / sum_t(Energy_t/(1+r)^t)
        # Simplified using a Capital Recovery Factor (CRF)
        crf = (discount_rate * (1 + discount_rate)**lifetime) / (((1 + discount_rate)**lifetime) - 1)
        annualized_capex = df["TOTAL CAPEX"] * crf
        annual_opex = df["TOTAL CAPEX"] * opex_percentage
        
        df["LCOE($/MWh)"] = (annualized_capex + annual_opex) / df["Yearly energy(MWh)"]
        df["Payback Period (Yrs)"] = df["TOTAL CAPEX"] / (df["Yearly energy(MWh)"] * 50) # Assuming $50/MWh price for simple payback
        
        return df

    @classmethod
    def _calculate_line_capex(cls, df, financial_constants):
        """
        Calculates the line capex based on connection distance, type, and voltage,
        utilizing the nested transmission configuration array.
        """
        transmission_rules = financial_constants.get("transmission", [])
        if not transmission_rules:
            return pd.Series([0.0] * len(df), index=df.index)
            
        line_capex = pd.Series([0.0] * len(df), index=df.index)
        
        for idx in df.index:
            row = df.loc[idx]
            capacity = row.get("Installed_Capacity_MW", 0)
            conn_type = row.get("Nearest_Connection_Type", "")
            conn_kv = row.get("Nearest_Connection_kV", 0)
            dist_km = row.get("Nearest_Connection_Distance_km", 0)
            
            if pd.isna(dist_km) or not conn_type:
                continue
                
            # Find the best matching rule
            matched_rule = None
            for r in transmission_rules:
                if (r.get("type", "").lower() == conn_type.lower() and
                    r.get("kv", 0) == conn_kv and
                    r.get("capacity_min", 0) <= capacity < r.get("capacity_max", 999999)):
                    matched_rule = r
                    break
                    
            if matched_rule:
                cost_per_km = matched_rule.get("cost_per_km", 0)
                fixed_cost = matched_rule.get("fixed_cost", 0)
                
                # Formual: Distance * Cost_per_KM + Fixed_Cost (if substation)
                # The fixed cost is essentially the Substation connection bay fee.
                if conn_type.lower() == "substation":
                    line_capex.at[idx] = (dist_km * cost_per_km) + fixed_cost
                else:
                    line_capex.at[idx] = (dist_km * cost_per_km)
            else:
                # Fallback purely on basic estimation if no rule matches
                line_capex.at[idx] = dist_km * 200000
                
        return line_capex

    @classmethod
    def _lookup_cp_values(cls, wind_speed_series, cp_values_list):
        """
        Performs a nearest-neighbor lookup of the CP value based on wind speed.
        Mimics Excel's XLOOKUP.
        """
        if not cp_values_list:
            return pd.Series([0.3] * len(wind_speed_series), index=wind_speed_series.index)
            
        cp_df = pd.DataFrame(cp_values_list)
        if "Wind speed" not in cp_df.columns or "Cp" not in cp_df.columns:
            return pd.Series([0.3] * len(wind_speed_series), index=wind_speed_series.index)
            
        # Ensure it's sorted and types match
        cp_df["Wind speed"] = cp_df["Wind speed"].astype(float)
        cp_df = cp_df.sort_values(by="Wind speed")
        
        # Use pandas merge_asof for extremely fast nearest-neighbor/XLOOKUP lookup
        target_df = pd.DataFrame({"TargetWind": wind_speed_series.astype(float)})
        target_df = target_df.sort_values("TargetWind")
        
        merged = pd.merge_asof(
            target_df, 
            cp_df, 
            left_on="TargetWind", 
            right_on="Wind speed",
            direction="nearest"
        )
        
        # Restore original index
        merged.index = target_df.index
        merged = merged.reindex(wind_speed_series.index)
        
        return merged["Cp"]
