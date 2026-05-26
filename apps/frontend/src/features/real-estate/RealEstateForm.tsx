import { Form, Formik } from "formik";
import { useMemo, useState } from "react";
import {
  FormikCheckbox,
  FormikNumberInput,
  FormikRadioGroup,
  FormikTextInput,
} from "../../shared/formik/controls";
import { realEstateSchema } from "../../shared/validation/realEstateSchema";
import { initialRealEstateValues, type RealEstateFormValues } from "./types";

const dealTypeOptions = [
  {
    label: "Продажа",
    value: "sale",
    description: "Объявление для прямой продажи объекта",
  },
  {
    label: "Аренда",
    value: "rent",
    description: "Объявление для долгосрочной аренды",
  },
] as const;

export function RealEstateForm() {
  const [submittedValues, setSubmittedValues] =
    useState<RealEstateFormValues | null>(null);
  const previewValues = useMemo(() => {
    if (!submittedValues) {
      return "После отправки здесь появится нормализованный payload объявления.";
    }

    return JSON.stringify(submittedValues, null, 2);
  }, [submittedValues]);

  return (
    <section className="listing-workspace" aria-labelledby="listing-title">
      <div className="listing-workspace__header">
        <p className="eyebrow">🏠 HomeOffer Pro</p>
        <h1 id="listing-title">Создание объявления о недвижимости</h1>
      </div>

      <Formik<RealEstateFormValues>
        initialValues={initialRealEstateValues}
        validationSchema={realEstateSchema}
        validateOnMount
        onSubmit={(values, helpers) => {
          setSubmittedValues(values);
          helpers.setSubmitting(false);
        }}
      >
        {({ isSubmitting, isValid, dirty }) => (
          <div className="listing-workspace__grid">
            <Form className="listing-form" noValidate>
              <div className="form-section">
                <div className="form-section__title">
                  <h2>📍 Объект</h2>
                  <span>Основные данные</span>
                </div>
                <div className="form-grid">
                  <FormikTextInput
                    name="name"
                    label="Название объекта"
                    placeholder="Например, 2-комнатная квартира"
                  />
                  <FormikTextInput
                    name="address"
                    label="Адрес"
                    placeholder="Город, улица, дом"
                  />
                  <FormikRadioGroup
                    name="dealType"
                    label="Тип сделки"
                    options={dealTypeOptions}
                  />
                  <FormikCheckbox
                    name="isStudio"
                    label="Студия"
                    description="Пометить объект как студию без отдельной жилой комнаты"
                  />
                </div>
              </div>

              <div className="form-section">
                <div className="form-section__title">
                  <h2>📐 Параметры дома</h2>
                  <span>Размеры и этажность</span>
                </div>
                <div className="form-grid form-grid--numbers">
                  <FormikNumberInput
                    name="floor"
                    label="Этаж"
                    min={-1}
                    placeholder="-1"
                  />
                  <FormikNumberInput
                    name="totalFloors"
                    label="Количество этажей в доме"
                    min={-3}
                    max={200}
                  />
                  <FormikNumberInput
                    name="square"
                    label="Площадь"
                    min={0}
                    max={400}
                  />
                  <FormikNumberInput
                    name="livingSquare"
                    label="Жилая площадь"
                    min={0}
                  />
                  <FormikNumberInput
                    name="kitchenSquare"
                    label="Площадь кухни"
                    min={0}
                  />
                </div>
              </div>

              <div className="listing-form__actions">
                <button
                  className="primary-button"
                  type="submit"
                  disabled={isSubmitting || !isValid || !dirty}
                >
                  {isSubmitting ? "Обработка..." : "Опубликовать объявление"}
                </button>
              </div>
            </Form>

            <aside className="payload-preview" aria-label="Payload объявления">
              <div>
                <p className="eyebrow">📋 JSON Preview</p>
                <h2>Данные объявления</h2>
              </div>
              <pre>{previewValues}</pre>
            </aside>
          </div>
        )}
      </Formik>
    </section>
  );
}
