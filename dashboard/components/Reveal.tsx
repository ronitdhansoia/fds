"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Stagger container for the orchestrated landing-page reveal — children that
 * pass an `order` prop fade up with an 80 ms stagger / 400 ms ease-out.
 */

export function RevealStack({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

export function RevealItem({
  order = 0,
  className,
  children,
}: {
  order?: number;
  className?: string;
  children: ReactNode;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 1, y: 0 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: reduce ? 0 : 0.4,
        delay: reduce ? 0 : order * 0.08,
        ease: [0.16, 1, 0.3, 1],
      }}
    >
      {children}
    </motion.div>
  );
}
