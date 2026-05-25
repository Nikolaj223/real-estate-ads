import * as Yup from "yup";
import "./moreThanSumOfFields";
import { MORE_THAN_SUM_OF_FIELDS_MESSAGE } from "./moreThanSumOfFields";
import { configureYupLocale } from "./yupLocale";

configureYupLocale();

const emptyStringToUndefined = (value: unknown, originalValue: unknown) =>
  originalValue === "" ? undefined : value;

const integerField = () =>
  Yup.number()
    .transform(emptyStringToUndefined)
    .integer("Значение должно быть целым числом")
    .required();

export const realEstateSchema = Yup.object({
  name: Yup.string().trim().required(),
  address: Yup.string().trim().required(),
  dealType: Yup.string().required(),
  isStudio: Yup.boolean().required(),
  floor: integerField().min(-1).max(Yup.ref("totalFloors")),
  totalFloors: integerField().min(-3).max(200),
  square: integerField()
    .min(0)
    .max(400)
    .moreThanSumOfFields(["livingSquare", "kitchenSquare"], MORE_THAN_SUM_OF_FIELDS_MESSAGE),
  livingSquare: integerField().min(0),
  kitchenSquare: integerField().min(0),
});
