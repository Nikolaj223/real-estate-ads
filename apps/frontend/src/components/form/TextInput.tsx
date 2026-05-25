import type { ChangeEventHandler, FocusEventHandler } from "react";
import { FieldShell } from "./FieldShell";

export type TextInputOwnProps = {
  label: string;
  placeholder?: string;
  helperText?: string;
  autoComplete?: string;
  disabled?: boolean;
};

export type TextInputInjectedProps = {
  name: string;
  value: string;
  onChange: ChangeEventHandler<HTMLInputElement>;
  onBlur: FocusEventHandler<HTMLInputElement>;
  error?: string;
};

export function TextInput({
  label,
  helperText,
  error,
  ...inputProps
}: TextInputOwnProps & TextInputInjectedProps) {
  return (
    <FieldShell label={label} helperText={helperText} error={error}>
      <input className="text-input" type="text" {...inputProps} />
    </FieldShell>
  );
}
