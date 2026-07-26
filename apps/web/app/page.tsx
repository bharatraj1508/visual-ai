import ChartTypes from "@/components/landing/ChartTypes";
import CtaBand from "@/components/landing/CtaBand";
import Hero from "@/components/landing/Hero";
import HowItWorks from "@/components/landing/HowItWorks";
import LandingFooter from "@/components/landing/LandingFooter";
import LandingNav from "@/components/landing/LandingNav";
import LandingShell from "@/components/landing/LandingShell";
import Showcase from "@/components/landing/Showcase";
import Thesis from "@/components/landing/Thesis";

export default function Home() {
  return (
    <LandingShell>
      <div className="min-h-screen bg-white">
        <LandingNav />
        <main>
          <Hero />
          <Thesis />
          <HowItWorks />
          <Showcase />
          <ChartTypes />
          <CtaBand />
        </main>
        <LandingFooter />
      </div>
    </LandingShell>
  );
}
