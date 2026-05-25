import { describe, expect, it } from "vitest";
import { ValidationError } from "yup";
import { realEstateSchema } from "../shared/validation/realEstateSchema";

const validPayload = {
  name: "2-комнатная квартира",
  address: "Москва, Тверская, 1",
  dealType: "sale",
  isStudio: false,
  floor: 3,
  totalFloors: 12,
  square: 70,
  livingSquare: 40,
  kitchenSquare: 12,
};

async function getValidationErrors(payload: unknown) {
  try {
    await realEstateSchema.validate(payload, { abortEarly: false });
    return {};
  } catch (error) {
    if (!(error instanceof ValidationError)) {
      throw error;
    }

    return error.inner.reduce<Record<string, string>>((errors, currentError) => {
      if (currentError.path && !errors[currentError.path]) {
        errors[currentError.path] = currentError.message;
      }

      return errors;
    }, {});
  }
}

describe("real estate validation schema", () => {
  it("uses global required, min and max messages", async () => {
    const errors = await getValidationErrors({
      ...validPayload,
      name: "",
      floor: -2,
      totalFloors: 201,
    });

    expect(errors.name).toBe("Поле обязательно для заполнения");
    expect(errors.floor).toBe("Значение не может быть меньше -1");
    expect(errors.totalFloors).toBe("Значение не может быть больше 200");
  });

  it("uses a local message for the total square rule", async () => {
    const errors = await getValidationErrors({
      ...validPayload,
      square: 45,
      livingSquare: 35,
      kitchenSquare: 10,
    });

    expect(errors.square).toBe("Общая площадь должна быть больше суммы жилой площади и площади кухни");
  });
});
