"use client";

import Link from "next/link";
import { MessageSquare, Sprout, Globe2, Sparkles, Leaf, TrendingUp } from "lucide-react";

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Decorative gradients */}
      <div className="pointer-events-none absolute -top-24 -right-24 h-[420px] w-[420px] rounded-full bg-[radial-gradient(circle_at_center,hsl(var(--brand-2)/0.22)_0%,transparent_60%)] float-slow" />

      {/* Top nav */}
      <header className="relative z-10 flex items-center justify-between px-6 sm:px-10 py-5">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-blue-600 via-fuchsia-500 to-amber-400" />
          <span className="font-semibold tracking-tight">ChipChip</span>
        </Link>
        <nav className="hidden sm:flex items-center gap-6 text-sm text-gray-600 dark:text-gray-300">
          <a href="#features" className="hover:text-gray-900 dark:hover:text-white transition-colors">Features</a>
          <a href="/chat" className="hover:text-gray-900 dark:hover:text-white transition-colors">Chat</a>
        </nav>
      </header>

      {/* Hero */}
      <main className="relative z-10 px-6 sm:px-10 pt-10 sm:pt-16 pb-16 sm:pb-24">
        <div className="mx-auto max-w-5xl">
          <div className="relative overflow-hidden rounded-3xl glass hero-glass p-6 sm:p-12 border border-white/10 shadow-xl bg-grid">
            <div className="pointer-events-none absolute inset-0 hero-veil" />
            <div className="max-w-3xl">
              <p className="text-xs uppercase tracking-widest text-gray-500">Horticulture • AI Assistant • Bilingual</p>
              <h1 className="mt-3 text-4xl sm:text-6xl font-semibold leading-[1.05] hero-text hero-text-lift">
                Buy. Sell. Learn.
                <br className="hidden sm:block" /> with an AI that speaks English and Amharic.
              </h1>
              <p className="mt-4 sm:mt-5 text-gray-600 dark:text-gray-300 text-base sm:text-lg">
                ChipChip helps customers and suppliers trade fresh produce, get pricing insights, and discover best practices — in real-time.
              </p>
              <div className="mt-7 sm:mt-8 flex flex-col sm:flex-row gap-3 sm:gap-4">
                <Link
                  href="/chat"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 text-white px-5 py-3 text-sm sm:text-base font-medium btn-glow"
                >
                  <MessageSquare className="h-4 w-4" /> Start Chat
                </Link>
                <a
                  href="#features"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-black/10 dark:border-white/15 px-5 py-3 text-sm sm:text-base"
                >
                  <Sparkles className="h-4 w-4" /> View Features
                </a>
              </div>
            </div>
          </div>

          {/* Features */}
          <section id="features" className="mt-10 sm:mt-16 grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
            <FeatureCard icon={<Sprout className="h-5 w-5" />} title="Product Knowledge">
              RAG-powered tips for storage, freshness, and seasonality across produce.
            </FeatureCard>
            <FeatureCard icon={<TrendingUp className="h-5 w-5" />} title="Pricing Insights">
              Supplier-friendly insights with competitor prices and smart suggestions.
            </FeatureCard>
            <FeatureCard icon={<Globe2 className="h-5 w-5" />} title="Bilingual Support">
              English, አማርኛ, and Amharic-Latin. Seamless switching during conversation.
            </FeatureCard>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-black/10 dark:border-white/10 px-6 sm:px-10 py-6 text-sm text-gray-600 dark:text-gray-300">
        <div className="mx-auto max-w-5xl flex items-center justify-between">
          <span>© {new Date().getFullYear()} ChipChip</span>
          <div className="flex items-center gap-5">
            <Link href="/chat" className="hover:underline">Start Chat</Link>
            <a href="#features" className="hover:underline">Features</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-black/10 dark:border-white/10 glass p-5 sm:p-6">
      <div className="absolute -top-12 -right-12 h-32 w-32 rounded-full bg-[radial-gradient(circle_at_center,hsl(var(--brand-3)/0.18)_0%,transparent_60%)] group-hover:scale-110 transition-transform" />
      <div className="relative z-10">
        <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">{icon}<span className="text-sm font-semibold tracking-tight">{title}</span></div>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{children}</p>
      </div>
    </div>
  );
}
