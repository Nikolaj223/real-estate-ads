import type { FocusEventHandler } from "react";

export type CheckboxOwnProps = {
  label: string;
  description?: string;
  disabled?: boolean;
};

export type CheckboxInjectedProps = {
  name: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  onBlur: FocusEventHandler<HTMLInputElement>;
  error?: string;
};

export function Checkbox({
  label,
  description,
  checked,
  onCheckedChange,
  error,
  ...inputProps
}: CheckboxOwnProps & CheckboxInjectedProps) {
  return (
    <label className="choice choice--checkbox">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onCheckedChange(event.target.checked)}
        {...inputProps}
      />
      <span className="choice__indicator" aria-hidden="true" />
      <span className="choice__content">
        <span className="choice__label">{label}</span>
        {description ? <span className="choice__description">{description}</span> : null}
        {error ? <span className="field-shell__error">{error}</span> : null}
      </span>
    </label>
  );
}
