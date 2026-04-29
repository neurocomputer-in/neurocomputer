import {
  Brain, Globe, Code, Briefcase, Terminal, Layers,
  Search, Pen, BarChart2, Folder, Mail, Calendar, StickyNote, Compass,
  Mic, Languages, Tv2, Sparkles,
} from 'lucide-react';

/** Single source of truth for the lucide icons referenced by `AppDef.icon`.
 *  Components that previously declared their own `ICON_MAP` should import
 *  this instead. */
export const ICON_MAP: Record<string, any> = {
  brain: Brain,
  globe: Globe,
  code: Code,
  briefcase: Briefcase,
  terminal: Terminal,
  layers: Layers,
  search: Search,
  pen: Pen,
  barchart: BarChart2,
  folder: Folder,
  mail: Mail,
  calendar: Calendar,
  note: StickyNote,
  compass: Compass,
  mic: Mic,
  languages: Languages,
  tv: Tv2,
  sparkles: Sparkles,
};
