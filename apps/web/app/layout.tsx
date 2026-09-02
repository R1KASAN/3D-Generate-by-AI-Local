import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Local 3D Generator",
  description: "Private local 3D generation service",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
