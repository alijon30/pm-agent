import Hero from "./components/Hero";
import Navbar from "./components/Navbar";

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-white">
        <div className="bg-gradient-to-br from-blue-200 via-slate-50 to-purple-300 relative overflow-hidden">
            <Navbar />
            <Hero />
        </div>
    </div>
  )
}

export default LandingPage;