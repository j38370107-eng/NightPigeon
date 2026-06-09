import { useEffect, useRef } from "react";
import { useLocation } from "wouter";

function StarCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const stars = Array.from({ length: 180 }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      r: Math.random() * 1.4 + 0.3,
      alpha: Math.random(),
      speed: Math.random() * 0.008 + 0.002,
      phase: Math.random() * Math.PI * 2,
    }));

    let frame = 0;
    let raf: number;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const t = frame * 0.012;
      for (const s of stars) {
        const alpha = 0.35 + 0.55 * Math.abs(Math.sin(t * s.speed * 60 + s.phase));
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${alpha})`;
        ctx.fill();
      }
      frame++;
      raf = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 1 }}
    />
  );
}

export default function Landing() {
  const [, setLocation] = useLocation();

  return (
    <div
      className="min-h-screen w-full flex flex-col items-center justify-center relative overflow-hidden"
      style={{
        backgroundImage: `url(${import.meta.env.BASE_URL}nightsky.png)`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
      }}
    >
      <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(8,10,22,0.45) 0%, rgba(12,14,28,0.6) 100%)", zIndex: 0 }} />
      <StarCanvas />

      <div className="relative flex flex-col items-center gap-10 px-6 text-center" style={{ zIndex: 2 }}>
        <div className="flex flex-col items-center gap-5">
          <div
            className="w-24 h-24 rounded-2xl overflow-hidden flex items-center justify-center"
            style={{
              border: "1.5px solid rgba(255,255,255,0.18)",
              boxShadow: "0 0 40px rgba(99,102,241,0.2), 0 0 80px rgba(124,58,237,0.08)",
              backdropFilter: "blur(8px)",
            }}
          >
            <img
              src={`${import.meta.env.BASE_URL}pigeon.jpeg`}
              alt="Night Pigeon"
              className="w-full h-full object-cover"
            />
          </div>

          <div>
            <h1
              className="text-6xl font-bold text-white tracking-tight"
              style={{
                textShadow: "0 0 60px rgba(129,140,248,0.3), 0 2px 12px rgba(0,0,0,0.6)",
                letterSpacing: "-0.02em",
              }}
            >
              Night Pigeon
            </h1>
            <p
              className="text-lg mt-3 max-w-sm font-light"
              style={{ color: "rgba(199,210,254,0.75)", textShadow: "0 1px 8px rgba(0,0,0,0.5)" }}
            >
              A private moderation bot for Discord, designed with large servers and reliability in mind.
            </p>
          </div>
        </div>

        <div className="flex gap-4">
          <button
            onClick={() => setLocation("/dashboard")}
            className="px-8 py-3 rounded-lg font-semibold text-white text-sm transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
            style={{
              background: "rgba(255,255,255,0.12)",
              border: "1.5px solid rgba(255,255,255,0.25)",
              backdropFilter: "blur(16px)",
              boxShadow: "0 4px 20px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.1)",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.18)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.4)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.12)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.25)";
            }}
          >
            Dashboard
          </button>

          <button
            onClick={() => setLocation("/docs")}
            className="px-8 py-3 rounded-lg font-semibold text-white text-sm transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
            style={{
              background: "rgba(255,255,255,0.12)",
              border: "1.5px solid rgba(255,255,255,0.25)",
              backdropFilter: "blur(16px)",
              boxShadow: "0 4px 20px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.1)",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.18)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.4)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.12)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.25)";
            }}
          >
            Wikipedia
          </button>
        </div>

        <div className="flex items-center gap-5 text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
          <a href="#" className="hover:text-white/60 transition-colors">GitHub</a>
          <span>·</span>
          <span>30+ plugins</span>
          <span>·</span>
          <span>YAML-based</span>
          <span>·</span>
          <a href="#" className="hover:text-white/60 transition-colors">Privacy Policy</a>
        </div>
      </div>
    </div>
  );
}
