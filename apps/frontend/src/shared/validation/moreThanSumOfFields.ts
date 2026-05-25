import { addMethod, number, type AnyObject, type Flags, type Maybe, type NumberSchema } from "yup";

declare module "yup" {
  interface NumberSchema<
    TType extends Maybe<number> = number | undefined,
    TContext = AnyObject,
    TDefault = undefined,
    TFlags extends Flags = "",
  > {
    moreThanSumOfFields(fields: readonly string[], message?: string): this;
  }
}

export const MORE_THAN_SUM_OF_FIELDS_MESSAGE =
  "Общая площадь должна быть больше суммы жилой площади и площади кухни";

const asNumber = (value: unknown) => {
  if (value === "" || value === null || value === undefined) {
    return 0;
  }

  const parsedValue = Number(value);
  return Number.isFinite(parsedValue) ? parsedValue : 0;
};

addMethod<NumberSchema>(
  number,
  "moreThanSumOfFields",
  function moreThanSumOfFields(fields: readonly string[], message?: string) {
    return this.test({
      name: "more-than-sum-of-fields",
      exclusive: true,
      message: message ?? MORE_THAN_SUM_OF_FIELDS_MESSAGE,
      test(value, context) {
        if (value === null || value === undefined) {
          return true;
        }

        const parent = context.parent as Record<string, unknown>;
        const fieldsSum = fields.reduce(
          (sum: number, fieldName: string) => sum + asNumber(parent[fieldName]),
          0,
        );

        return Number(value) > fieldsSum;
      },
    });
  },
);
