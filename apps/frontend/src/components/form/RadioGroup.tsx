import type { FocusEventHandler } from "react";

export type RadioOption = {
  label: string;
  value: string;
  description?: string;
};

export type RadioGroupOwnProps = {
  label: string;
  options: readonly RadioOption[];
  disabled?: boolean;
};

export type RadioGroupInjectedProps = {
  name: string;
  value: string;
  onValueChange: (value: string) => void;
  onBlur: FocusEventHandler<HTMLInputElement>;
  error?: string;
};

export function RadioGroup({
  label,
  options,
  name,
  value,
  onValueChange,
  onBlur,
  disabled,
  error,
}: RadioGroupOwnProps & RadioGroupInjectedProps) {
  return (
    <fieldset className="radio-group">
      <legend>{label}</legend>
      <div className="radio-group__options">
        {options.map((option) => (
          <label className="choice choice--radio" key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onValueChange(option.value)}
              onBlur={onBlur}
              disabled={disabled}
            />
            <span className="choice__indicator" aria-hidden="true" />
            <span className="choice__content">
              <span className="choice__label">{option.label}</span>
              {option.description ? <span className="choice__description">{option.description}</span> : null}
            </span>
          </label>
        ))}
      </div>
      {error ? <span className="field-shell__error">{error}</span> : null}
    </fieldset>
  );
}
