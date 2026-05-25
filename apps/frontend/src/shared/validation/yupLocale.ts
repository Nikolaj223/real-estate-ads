import { setLocale } from "yup";

let configured = false;

export function configureYupLocale() {
  if (configured) {
    return;
  }

  setLocale({
    mixed: {
      required: "Поле обязательно для заполнения",
    },
    number: {
      min: ({ min }) => `Значение не может быть меньше ${min}`,
      max: ({ max }) => `Значение не может быть больше ${max}`,
    },
  });

  configured = true;
}
