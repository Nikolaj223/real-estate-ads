import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Form, Formik, useFormikContext } from "formik";
import { describe, expect, it, vi } from "vitest";
import { FormikCheckbox, FormikRadioGroup } from "../shared/formik/controls";

type TestValues = {
  isStudio: boolean;
  dealType: string;
};

function ValuesProbe() {
  const { values } = useFormikContext<TestValues>();
  return <output data-testid="values">{JSON.stringify(values)}</output>;
}

describe("Formik-bound controls", () => {
  it("updates checkbox and radio values without passing manual Formik handlers", async () => {
    const user = userEvent.setup();

    render(
      <Formik<TestValues> initialValues={{ isStudio: false, dealType: "sale" }} onSubmit={vi.fn()}>
        <Form>
          <FormikCheckbox name="isStudio" label="Студия" />
          <FormikRadioGroup
            name="dealType"
            label="Тип сделки"
            options={[
              { label: "Продажа", value: "sale" },
              { label: "Аренда", value: "rent" },
            ]}
          />
          <ValuesProbe />
        </Form>
      </Formik>,
    );

    await user.click(screen.getByRole("checkbox", { name: "Студия" }));
    await user.click(screen.getByRole("radio", { name: "Аренда" }));

    expect(screen.getByRole("checkbox", { name: "Студия" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Аренда" })).toBeChecked();
    expect(screen.getByTestId("values")).toHaveTextContent(
      JSON.stringify({ isStudio: true, dealType: "rent" }),
    );
  });
});
