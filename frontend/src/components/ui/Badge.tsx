import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Badge.module.css";

type Variant = "success" | "danger" | "info" | "neutral" | "warning";

interface Props extends HTMLAttributes<HTMLSpanElement> {
  variant?: Variant;
  children: ReactNode;
}

export function Badge({ variant = "neutral", children, className, ...rest }: Props) {
  const cls = [styles.badge, styles[`v-${variant}`], className ?? ""]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={cls} {...rest}>
      {children}
    </span>
  );
}
