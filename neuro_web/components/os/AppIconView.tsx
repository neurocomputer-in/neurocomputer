'use client';
import Image from 'next/image';
import { Globe } from 'lucide-react';
import { ICON_MAP } from '@/lib/iconMap';
import type { AppDef } from '@/lib/appRegistry';

/**
 * Renders an app's branded PNG (`AppDef.iconImage`) when available, otherwise
 * falls back to its lucide glyph (`AppDef.icon`). All grid/dock/tab/picker
 * surfaces should use this so the four branded apps render identically
 * everywhere.
 */
export default function AppIconView({
  app,
  size = 18,
  color,
  fill = false,
}: {
  app: AppDef;
  size?: number;
  color?: string;
  fill?: boolean;
}) {
  if (app.iconImage) {
    if (fill) {
      // eslint-disable-next-line @next/next/no-img-element
      return <img src={app.iconImage} alt={app.name} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />;
    }
    return (
      <Image
        src={app.iconImage}
        alt={app.name}
        width={size}
        height={size}
        style={{ objectFit: 'contain' }}
      />
    );
  }
  const LucideIcon = ICON_MAP[app.icon] || Globe;
  return <LucideIcon size={size} color={color ?? '#fff'} strokeWidth={1.8} />;
}
