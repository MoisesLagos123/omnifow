import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Badge.module.css";

type Variant = "success" | "danger" | "info" | "neutral" | "warning" | "brand";
type Size = "sm" | "md";

interface Props extends HTMLAttributes<HTMLSpanElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
}

export function Badge({ variant = "neutral", size = "md", children, className, ...rest }: Props) {
  const cls = [
    styles.badge,
    styles[`v-${variant}`],
    size === "sm" ? styles["size-sm"] : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={cls} {...rest}>
      {children}
    </span>
  );
}
