import type { HTMLAttributes } from "react";
import styles from "./Skeleton.module.css";

interface Props extends HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  rounded?: boolean;
}

export function Skeleton({ width, height, rounded, style, className, ...rest }: Props) {
  return (
    <div
      className={`${styles.skeleton} ${rounded ? styles.rounded : ""} ${className ?? ""}`}
      style={{ width, height, ...style }}
      aria-hidden="true"
      {...rest}
    />
  );
}
