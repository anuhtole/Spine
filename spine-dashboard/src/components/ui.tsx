import type { ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

export function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

/* ——— Layout ——— */

export function PageHeader({
  title,
  description,
  actions,
  badge,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  badge?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight text-spine-fg">{title}</h1>
          {badge}
        </div>
        {description ? (
          <p className="max-w-2xl text-sm leading-relaxed text-spine-muted">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

/* ——— Surfaces ——— */

export function Card({
  children,
  className,
  padding = false,
}: {
  children: ReactNode;
  className?: string;
  padding?: boolean;
}) {
  return (
    <div className={cx("surface-panel overflow-hidden", padding && "p-6", className)}>{children}</div>
  );
}

export function CardHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-spine-border px-6 py-4">
      <div className="min-w-0">
        <div className="text-sm font-medium text-spine-fg">{title}</div>
        {subtitle ? <p className="mt-0.5 text-sm text-spine-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function CardBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("p-6", className)}>{children}</div>;
}

export function MetricCard({
  label,
  value,
  hint,
  trend,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  trend?: "up" | "down" | "neutral";
}) {
  return (
    <div className="surface-panel p-5 transition-colors hover:border-spine-border-strong">
      <p className="text-2xs font-medium uppercase tracking-wider text-spine-subtle">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-spine-fg tabular-nums">{value}</p>
      {hint ? (
        <p
          className={cx(
            "mt-1.5 text-xs",
            trend === "up" && "text-spine-success",
            trend === "down" && "text-spine-danger",
            (!trend || trend === "neutral") && "text-spine-subtle",
          )}
        >
          {hint}
        </p>
      ) : null}
    </div>
  );
}

/* ——— Actions ——— */

export function Button({
  children,
  type = "button",
  variant = "primary",
  size = "md",
  className,
  disabled,
  onClick,
}: {
  children: ReactNode;
  type?: "button" | "submit" | "reset";
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
}) {
  const base =
    "inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 disabled:pointer-events-none disabled:opacity-40";
  const sizes = {
    sm: "rounded-lg px-3 py-1.5 text-xs",
    md: "rounded-lg px-4 py-2 text-sm",
  };
  const variants = {
    primary:
      "bg-white text-zinc-950 shadow-sm hover:bg-zinc-100 active:scale-[0.98]",
    secondary:
      "border border-spine-border-strong bg-spine-elevated text-spine-fg hover:bg-spine-hover hover:border-white/20",
    ghost: "text-spine-muted hover:bg-spine-hover hover:text-spine-fg",
    danger:
      "border border-red-500/30 bg-red-500/10 text-red-300 hover:bg-red-500/15",
  };
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={cx(base, sizes[size], variants[variant], className)}
    >
      {children}
    </button>
  );
}

/* ——— Forms ——— */

export function Field({
  label,
  children,
  hint,
  className,
}: {
  label: ReactNode;
  children: ReactNode;
  hint?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="block text-xs font-medium text-spine-muted">{label}</label>
      <div className="mt-1.5">{children}</div>
      {hint ? <p className="mt-1 text-2xs text-spine-subtle">{hint}</p> : null}
    </div>
  );
}

const inputClass =
  "w-full rounded-lg border border-spine-border bg-spine-bg px-3 py-2 text-sm text-spine-fg placeholder:text-spine-subtle transition-colors hover:border-spine-border-strong focus:border-spine-accent-strong/50 focus:ring-1 focus:ring-spine-accent-strong/30";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const { className, ...rest } = props;
  return <input {...rest} className={cx(inputClass, className)} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const { className, ...rest } = props;
  return <textarea {...rest} className={cx(inputClass, "resize-y min-h-[80px]", className)} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  const { className, children, ...rest } = props;
  return (
    <select {...rest} className={cx(inputClass, className)}>
      {children}
    </select>
  );
}

/* ——— Feedback ——— */

export function Badge({
  children,
  variant = "default",
}: {
  children: ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "accent" | "muted";
}) {
  const styles = {
    default: "bg-spine-elevated text-spine-muted ring-1 ring-spine-border",
    success: "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/25",
    warning: "bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/25",
    danger: "bg-red-500/10 text-red-300 ring-1 ring-red-500/25",
    accent: "bg-spine-accent-muted text-spine-accent ring-1 ring-indigo-500/25",
    muted: "bg-spine-elevated/80 text-spine-subtle",
  };
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-md px-2 py-0.5 text-2xs font-medium capitalize",
        styles[variant],
      )}
    >
      {children}
    </span>
  );
}

export function LiveIndicator({ live, label = "Live" }: { live: boolean; label?: string }) {
  if (!live) return null;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-0.5 text-2xs font-medium text-emerald-400">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-soft" />
      {label}
    </span>
  );
}

export function Alert({
  children,
  variant = "info",
}: {
  children: ReactNode;
  variant?: "info" | "success" | "warning" | "error";
}) {
  const styles = {
    info: "border-spine-border bg-spine-elevated text-spine-muted",
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-100",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-100",
    error: "border-red-500/30 bg-red-500/10 text-red-200",
  };
  return (
    <div className={cx("rounded-lg border px-4 py-3 text-sm", styles[variant])}>{children}</div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-spine-border bg-spine-elevated">
        <svg className="h-5 w-5 text-spine-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
      </div>
      <p className="text-sm font-medium text-spine-fg">{title}</p>
      {description ? <p className="mt-1 max-w-sm text-sm text-spine-muted">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cx(
        "h-4 w-4 animate-spin rounded-full border-2 border-spine-border border-t-spine-fg",
        className,
      )}
    />
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded-lg bg-spine-elevated", className)} />;
}

/* ——— Decision helpers ——— */

export function decisionBadgeVariant(
  decision: string | null | undefined,
): "success" | "danger" | "warning" | "muted" {
  if (decision === "allowed") return "success";
  if (decision === "blocked") return "danger";
  if (decision === "flagged") return "warning";
  return "muted";
}

export function riskTone(score: number): string {
  if (score >= 0.8) return "text-spine-danger";
  if (score >= 0.5) return "text-spine-warning";
  return "text-spine-success";
}
