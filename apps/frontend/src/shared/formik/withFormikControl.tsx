import type { ComponentType } from "react";
import type { FieldHelperProps, FieldInputProps, FieldMetaProps } from "formik";
import { useField } from "formik";

export type FormikControlProps<Value> = {
  name: string;
  validate?: (value: Value) => string | undefined | Promise<string | undefined>;
};

type AdapterArgs<Value, OwnProps extends object> = {
  name: string;
  props: OwnProps;
  field: FieldInputProps<Value>;
  meta: FieldMetaProps<Value>;
  helpers: FieldHelperProps<Value>;
};

type Adapter<Value, OwnProps extends object, InjectedProps extends object> = (
  args: AdapterArgs<Value, OwnProps>,
) => InjectedProps;

export function withFormikControl<Value, OwnProps extends object, InjectedProps extends object>(
  Component: ComponentType<OwnProps & InjectedProps>,
  adapter: Adapter<Value, OwnProps, InjectedProps>,
) {
  return function FormikBoundControl(props: OwnProps & FormikControlProps<Value>) {
    const { name, validate, ...ownProps } = props;
    const [field, meta, helpers] = useField<Value>({ name, validate });
    const injectedProps = adapter({
      name,
      props: ownProps as OwnProps,
      field,
      meta,
      helpers,
    });

    return <Component {...(ownProps as OwnProps)} {...injectedProps} />;
  };
}
