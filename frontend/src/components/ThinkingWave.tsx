import { cn } from "@/lib/utils"

interface Props {
  text?: string
  className?: string
}

export default function ThinkingWave({ text = "", className }: Props) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Wave bars */}
      <div className="flex items-center gap-1">
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="block h-3.5 w-1 rounded-full bg-primary"
            style={{
              animation: `waveBar 1.2s ease-in-out infinite`,
              animationDelay: `${i * 0.12}s`,
            }}
          />
        ))}
      </div>
      {text ? (
        <span className="text-sm text-muted-foreground select-none">{text}</span>
      ) : null}

      <style>{`
        @keyframes waveBar {
          0%, 40%, 100% {
            opacity: 0.25;
            transform: scaleY(0.4);
          }
          20% {
            opacity: 1;
            transform: scaleY(1.3);
          }
        }
      `}</style>
    </div>
  )
}
