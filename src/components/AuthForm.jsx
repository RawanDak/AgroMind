import "./AuthForm.css";

function AuthForm({
  title,
  fields,
  values,
  onChange,
  onSubmit,
  buttonText,
  message,
  children,
}) {
  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <h1>{title}</h1>

        {fields.map((field) => (
          <input
            key={field.name}
            type={field.type}
            name={field.name}
            placeholder={field.placeholder}
            value={values[field.name]}
            onChange={onChange}
            required={field.required}
          />
        ))}

        <button type="submit">{buttonText}</button>

        {message && <p className="auth-message">{message}</p>}
        {children}
      </form>
    </div>
  );
}

export default AuthForm;
