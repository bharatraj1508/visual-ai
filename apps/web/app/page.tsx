import ChartTypes from "@/components/landing/ChartTypes";
import CtaBand from "@/components/landing/CtaBand";
import DashboardShowcase from "@/components/landing/DashboardShowcase";
import DataPipeline from "@/components/landing/DataPipeline";
import Faq from "@/components/landing/Faq";
import Hero from "@/components/landing/Hero";
import HowItWorks from "@/components/landing/HowItWorks";
import LandingFooter from "@/components/landing/LandingFooter";
import LandingNav from "@/components/landing/LandingNav";
import LandingShell from "@/components/landing/LandingShell";
import Pricing from "@/components/landing/Pricing";
import ProblemStatement from "@/components/landing/ProblemStatement";
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
          <DataPipeline />
          <Showcase />
          <ProblemStatement />
          <DashboardShowcase />
          <ChartTypes />
          <Pricing />
          <Faq />
          <CtaBand />
        </main>
        <LandingFooter />
      </div>
    </LandingShell>
  );
}
