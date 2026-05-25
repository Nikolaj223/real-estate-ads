import {
  Checkbox,
  type CheckboxInjectedProps,
  type CheckboxOwnProps,
} from "../../components/form/Checkbox";
import {
  NumberInput,
  type NumberInputInjectedProps,
  type NumberInputOwnProps,
  type NumericFormValue,
} from "../../components/form/NumberInput";
import {
  RadioGroup,
  type RadioGroupInjectedProps,
  type RadioGroupOwnProps,
} from "../../components/form/RadioGroup";
import {
  TextInput,
  type TextInputInjectedProps,
  type TextInputOwnProps,
} from "../../components/form/TextInput";
import { withFormikControl } from "./withFormikControl";

const visibleError = (touched: boolean, error?: string) => (touched ? error : undefined);

export const FormikTextInput = withFormikControl<string, TextInputOwnProps, TextInputInjectedProps>(
  TextInput,
  ({ name, field, meta }) => ({
    name,
    value: field.value ?? "",
    onChange: field.onChange,
    onBlur: field.onBlur,
    error: visibleError(meta.touched, meta.error),
  }),
);

export const FormikNumberInput = withFormikControl<
  NumericFormValue,
  NumberInputOwnProps,
  NumberInputInjectedProps
>(NumberInput, ({ name, field, meta, helpers }) => ({
  name,
  value: field.value ?? "",
  onValueChange: (value) => helpers.setValue(value),
  onBlur: field.onBlur,
  error: visibleError(meta.touched, meta.error),
}));

export const FormikCheckbox = withFormikControl<boolean, CheckboxOwnProps, CheckboxInjectedProps>(
  Checkbox,
  ({ name, field, meta, helpers }) => ({
    name,
    checked: Boolean(field.value),
    onCheckedChange: (checked) => helpers.setValue(checked),
    onBlur: field.onBlur,
    error: visibleError(meta.touched, meta.error),
  }),
);

export const FormikRadioGroup = withFormikControl<string, RadioGroupOwnProps, RadioGroupInjectedProps>(
  RadioGroup,
  ({ name, field, meta, helpers }) => ({
    name,
    value: field.value ?? "",
    onValueChange: (value) => helpers.setValue(value),
    onBlur: field.onBlur,
    error: visibleError(meta.touched, meta.error),
  }),
);
