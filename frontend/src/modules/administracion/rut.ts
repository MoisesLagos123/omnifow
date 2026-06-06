/**
 * Validación de RUT chileno (módulo 11).
 * Acepta formato con o sin puntos y con guión: "12.345.678-9", "12345678-9", "123456789".
 * Retorna el RUT canónico "12345678-9" o null si es inválido.
 */
export function validarRut(input: string): string | null {
  if (!input) return null;
  const cleaned = input.replace(/[^0-9kK]/g, "").toUpperCase();
  if (cleaned.length < 2 || cleaned.length > 9) return null;
  const cuerpo = cleaned.slice(0, -1);
  const dv = cleaned.slice(-1);
  if (!/^\d+$/.test(cuerpo)) return null;

  // Cálculo módulo 11
  let suma = 0;
  let multiplicador = 2;
  for (let i = cuerpo.length - 1; i >= 0; i--) {
    suma += Number(cuerpo[i]) * multiplicador;
    multiplicador = multiplicador === 7 ? 2 : multiplicador + 1;
  }
  const resto = 11 - (suma % 11);
  let dvCalc: string;
  if (resto === 11) dvCalc = "0";
  else if (resto === 10) dvCalc = "K";
  else dvCalc = String(resto);

  if (dvCalc !== dv) return null;
  return `${cuerpo}-${dv}`;
}

/** Formatea un RUT canónico añadiendo separadores de miles. */
export function formatearRut(rut: string): string {
  const m = /^(\d+)-([\dkK])$/.exec(rut);
  if (!m) return rut;
  const [, cuerpo, dv] = m;
  const conPuntos = cuerpo!.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${conPuntos}-${dv!.toUpperCase()}`;
}
