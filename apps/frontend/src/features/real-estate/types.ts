import type { NumericFormValue } from "../../components/form/NumberInput";

export type DealType = "sale" | "rent";

export type RealEstateFormValues = {
  name: string;
  address: string;
  dealType: DealType;
  isStudio: boolean;
  floor: NumericFormValue;
  totalFloors: NumericFormValue;
  square: NumericFormValue;
  livingSquare: NumericFormValue;
  kitchenSquare: NumericFormValue;
};

export const initialRealEstateValues: RealEstateFormValues = {
  name: "",
  address: "",
  dealType: "sale",
  isStudio: false,
  floor: "",
  totalFloors: "",
  square: "",
  livingSquare: "",
  kitchenSquare: "",
};
