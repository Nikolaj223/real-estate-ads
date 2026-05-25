import type { ReactNode } from "react";

type FieldShellProps = {
  label?: string;
  helperText?: string;
  error?: string;
  children: ReactNode;
};

export function FieldShell({ label, helperText, error, children }: FieldShellProps) {
  return (
    <label className="field-shell">
      {label ? <span className="field-shell__label">{label}</span> : null}
      {children}
      {error ? <span className="field-shell__error">{error}</span> : null}
      {!error && helperText ? <span className="field-shell__helper">{helperText}</span> : null}
    </label>
  );
}
