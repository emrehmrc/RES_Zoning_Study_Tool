import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Renewable Energy Zoning Dashboard',
  description: 'GIS Grid & Scoring Dashboard for Solar and Wind Energy Zoning',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  )
}
