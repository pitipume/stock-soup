import Link from "next/link";

const links = [
  { href: "/vi", label: "VI Scanner", active: true },
  { href: "/bot", label: "Trading Bot", active: true },
  { href: "/lab", label: "Formula Lab", active: false },
];

export default function Nav() {
  return (
    <header className="border-b border-zinc-800 bg-zinc-950">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6 overflow-x-auto flex-shrink-0 whitespace-nowrap">
        <Link href="/" className="font-bold text-lg tracking-tight text-white">
          Stock<span className="text-emerald-400">Soup</span>
        </Link>
        <nav className="flex gap-1">
          {links.map((link) =>
            link.active ? (
              <Link
                key={link.href}
                href={link.href}
                className="px-3 py-1.5 text-sm rounded-md text-zinc-100 hover:bg-zinc-800 transition-colors"
              >
                {link.label}
              </Link>
            ) : (
              <span
                key={link.href}
                className="px-3 py-1.5 text-sm rounded-md text-zinc-600 cursor-not-allowed"
                title="Coming in Phase 2"
              >
                {link.label}
              </span>
            )
          )}
        </nav>
      </div>
    </header>
  );
}
