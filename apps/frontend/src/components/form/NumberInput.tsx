import type { FocusEventHandler } from "react";
import { FieldShell } from "./FieldShell";

export type NumericFormValue = number | "";

export type NumberInputOwnProps = {
  label: string;
  placeholder?: string;
  helperText?: string;
  min?: number;
  max?: number;
  disabled?: boolean;
};

export type NumberInputInjectedProps = {
  name: string;
  value: NumericFormValue;
  onValueChange: (value: NumericFormValue) => void;
  onBlur: FocusEventHandler<HTMLInputElement>;
  error?: string;
};

export function NumberInput({
  label,
  helperText,
  error,
  value,
  onValueChange,
  ...inputProps
}: NumberInputOwnProps & NumberInputInjectedProps) {
  return (
    <FieldShell label={label} helperText={helperText} error={error}>
      <input
        className="text-input"
        type="number"
        inputMode="numeric"
        value={value}
        onChange={(event) => {
          const nextValue = event.target.value;
          onValueChange(nextValue === "" ? "" : Number(nextValue));
        }}
        {...inputProps}
      />
    </FieldShell>
  );
}
