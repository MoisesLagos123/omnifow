import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, ChevronDown, ShieldCheck } from "lucide-react";

import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Badge } from "../../components/ui/Badge";
import { ErrorAlert } from "../../components/ui/ErrorAlert";
import { Skeleton } from "../../components/ui/Skeleton";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { PageHeader } from "../../components/ui/PageHeader";
import {
  MultiSelect,
  type MultiSelectOption,
} from "../../components/ui/MultiSelect";
import { useToast } from "../../components/ui/Toast";
import { adminApi, type Perfil, type UsuarioAdmin } from "../../api/admin";
import {
  sucursalesApi,
  type SucursalConContadores,
} from "../../api/sucursales";
import { describeError } from "../../api/errorMessages";
import { editarUsuarioSchema, type EditarUsuarioFormValues } from "./schemas";
import { formatearRut } from "./rut";
import { ROUTES } from "../../routePaths";
import styles from "./AdminPages.module.css";

export function EditarUsuarioPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const [usuario, setUsuario] = useState<UsuarioAdmin | null>(null);
  const [perfiles, setPerfiles] = useState<Perfil[]>([]);
  const [sucursalesDisponibles, setSucursalesDisponibles] = useState<
    SucursalConContadores[]
  >([]);
  const [sucursalIds, setSucursalIds] = useState<string[]>([]);
  const [sucursalIdsInicial, setSucursalIdsInicial] = useState<string[]>([]);
  const [savingSucursales, setSavingSucursales] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [permisosOpen, setPermisosOpen] = useState(false);
  const [reload, setReload] = useState(0);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<EditarUsuarioFormValues>({
    resolver: zodResolver(editarUsuarioSchema),
    mode: "onTouched",
    defaultValues: { nombre: "", email: "", perfiles_ids: [] },
  });

  useEffect(() => {
    if (!id) return;
    const ctl = new AbortController();
    setLoadError(null);
    Promise.all([
      adminApi.obtenerUsuario(id, ctl.signal),
      adminApi.listPerfiles({ activo: true, limit: 200 }, ctl.signal),
      sucursalesApi.listSucursales(
        { activo: true, limit: 200 },
        ctl.signal
      ),
    ])
      .then(([u, perfRes, sucRes]) => {
        setUsuario(u);
        setPerfiles(perfRes.items);
        setSucursalesDisponibles(sucRes.items);
        const ids = (u.sucursales ?? []).map((s) => s.id);
        setSucursalIds(ids);
        setSucursalIdsInicial(ids);
        reset({
          nombre: u.nombre,
          email: u.email,
          perfiles_ids: u.perfiles.map((p) => p.id),
        });
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setLoadError(describeError(err));
      });
    return () => ctl.abort();
  }, [id, reset, reload]);

  const perfilOptions: MultiSelectOption[] = useMemo(
    () =>
      perfiles.map((p) => ({
        value: p.id,
        label: p.nombre,
        hint: p.descripcion ?? undefined,
      })),
    [perfiles]
  );

  const sucursalOptions: MultiSelectOption[] = useMemo(
    () =>
      sucursalesDisponibles.map((s) => ({
        value: s.id,
        label: s.nombre,
        hint: s.codigo,
      })),
    [sucursalesDisponibles]
  );

  const sucursalesDirty = useMemo(() => {
    if (sucursalIds.length !== sucursalIdsInicial.length) return true;
    const setIni = new Set(sucursalIdsInicial);
    return sucursalIds.some((x) => !setIni.has(x));
  }, [sucursalIds, sucursalIdsInicial]);

  // Permisos efectivos derivados de los perfiles del usuario
  const permisosEfectivos = useMemo(() => {
    if (!usuario) return [] as string[];
    return usuario.permisos;
  }, [usuario]);

  const permisosAgrupados = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const code of permisosEfectivos) {
      const recurso = code.split(".")[0] ?? "otros";
      const arr = map.get(recurso) ?? [];
      arr.push(code);
      map.set(recurso, arr);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [permisosEfectivos]);

  async function onSubmit(values: EditarUsuarioFormValues) {
    if (!id) return;
    setServerError(null);
    try {
      // El formulario interno usa `perfiles_ids`, el backend espera `perfil_ids`.
      let updated = await adminApi.actualizarUsuario(id, {
        nombre: values.nombre,
        email: values.email,
        perfil_ids: values.perfiles_ids,
      });
      if (sucursalesDirty) {
        setSavingSucursales(true);
        updated = await sucursalesApi.asignarSucursalesAUsuario(
          id,
          sucursalIds
        );
      }
      setUsuario(updated);
      const nuevasIds = (updated.sucursales ?? []).map((s) => s.id);
      setSucursalIds(nuevasIds);
      setSucursalIdsInicial(nuevasIds);
      reset({
        nombre: updated.nombre,
        email: updated.email,
        perfiles_ids: updated.perfiles.map((p) => p.id),
      });
      toast.success("Cambios guardados");
    } catch (err) {
      setServerError(describeError(err));
    } finally {
      setSavingSucursales(false);
    }
  }

  async function handleDeactivate() {
    if (!id) return;
    try {
      await adminApi.desactivarUsuario(id);
      toast.success("Usuario desactivado");
      navigate(ROUTES.ADMIN_USUARIOS);
    } catch (err) {
      toast.error("No se pudo desactivar", describeError(err));
    }
  }

  if (loadError) {
    return (
      <div className={styles.detail}>
        <ErrorAlert>{loadError}</ErrorAlert>
        <Button
          variant="ghost"
          onClick={() => setReload((r) => r + 1)}
        >
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.detail}>
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(ROUTES.ADMIN_USUARIOS)}
          leftIcon={<ArrowLeft size={16} />}
        >
          Volver a usuarios
        </Button>
      </div>

      <PageHeader
        eyebrow="Administración"
        title={
          usuario ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
              {usuario.nombre}
              {usuario.activo ? (
                <Badge variant="success" size="sm">Activo</Badge>
              ) : (
                <Badge variant="neutral" size="sm">Inactivo</Badge>
              )}
            </span>
          ) : (
            <Skeleton width={220} />
          )
        }
        subtitle={
          usuario ? (
            <>
              <span className={styles.mono}>{formatearRut(usuario.rut)}</span>
              {" · "}
              {usuario.email}
            </>
          ) : (
            <Skeleton width={160} />
          )
        }
      />

      <div className={styles.detailCols}>
        {/* ── Columna izquierda: datos + permisos efectivos ─────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <Card className={styles.formCard}>
            <form onSubmit={handleSubmit(onSubmit)} noValidate>
              {serverError && <ErrorAlert>{serverError}</ErrorAlert>}

              <Input
                label="Nombre completo"
                error={errors.nombre?.message}
                {...register("nombre")}
              />
              <Input
                label="Email"
                type="email"
                error={errors.email?.message}
                {...register("email")}
              />
              <Input
                label="RUT"
                value={usuario ? formatearRut(usuario.rut) : ""}
                readOnly
                hint="El RUT no se puede modificar."
                style={{ fontFamily: "var(--font-mono)" }}
              />

              <div className={styles.formActions}>
                <Button
                  type="submit"
                  loading={isSubmitting || savingSucursales}
                  disabled={
                    (!isDirty && !sucursalesDirty) ||
                    isSubmitting ||
                    savingSucursales
                  }
                >
                  Guardar cambios
                </Button>
              </div>
            </form>
          </Card>

          {/* Permisos efectivos (colapsible) */}
          <div className={styles.collapsible}>
            <button
              type="button"
              className={styles.collapsibleBtn}
              onClick={() => setPermisosOpen((o) => !o)}
              aria-expanded={permisosOpen}
            >
              <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)" }}>
                <ShieldCheck size={15} aria-hidden="true" />
                Permisos efectivos ({permisosEfectivos.length})
              </span>
              <ChevronDown
                size={16}
                aria-hidden="true"
                style={{
                  transform: permisosOpen ? "rotate(180deg)" : "none",
                  transition: "transform var(--transition-fast)",
                }}
              />
            </button>
            {permisosOpen && (
              <div className={styles.collapsibleBody}>
                {permisosEfectivos.length === 0 ? (
                  <p className={styles.muted}>
                    Este usuario no tiene permisos asignados.
                  </p>
                ) : (
                  permisosAgrupados.map(([recurso, codigos]) => (
                    <div key={recurso} className={styles.permGroup}>
                      <div className={styles.permGroupHeader}>
                        <span>{recurso}</span>
                        <span className={styles.permGroupCount}>
                          {codigos.length} permisos
                        </span>
                      </div>
                      <div className={styles.permList}>
                        {codigos.map((c) => (
                          <div key={c} className={styles.permRow}>
                            <span className={styles.permCode}>{c}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {usuario?.activo && (
            <div className={styles.dangerZone}>
              <div>
                <p className={styles.dangerLabel}>Desactivar usuario</p>
                <p className={styles.dangerHelp}>
                  No podrá iniciar sesión. Sus datos y trazabilidad se preservan.
                </p>
              </div>
              <Button
                variant="danger-ghost"
                onClick={() => setConfirmOpen(true)}
              >
                Desactivar
              </Button>
            </div>
          )}
        </div>

        {/* ── Columna derecha: perfiles + sucursales ───────────────── */}
        <div className={styles.sideCards}>
          {/* Perfiles */}
          <Card style={{ padding: "var(--space-4)" }}>
            <p className={styles.sideCardTitle}>Perfiles asignados</p>
            <Controller
              name="perfiles_ids"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <MultiSelect
                    label=""
                    options={perfilOptions}
                    value={field.value}
                    onChange={field.onChange}
                    error={fieldState.error?.message}
                    placeholder="Selecciona perfiles..."
                  />
                </>
              )}
            />
          </Card>

          {/* Sucursales */}
          <Card style={{ padding: "var(--space-4)" }}>
            <p className={styles.sideCardTitle}>Sucursales con acceso</p>
            <MultiSelect
              label=""
              options={sucursalOptions}
              value={sucursalIds}
              onChange={setSucursalIds}
              placeholder="Sin restricción — todas las sucursales"
            />
            <p className={styles.muted} style={{ marginTop: "var(--space-2)", fontSize: "var(--font-xs)" }}>
              Vacío = acceso a todas las sucursales.
            </p>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Desactivar usuario"
        description={
          usuario
            ? `¿Confirmas que deseas desactivar a "${usuario.nombre}"? Podrás reactivarlo más adelante.`
            : ""
        }
        confirmLabel="Desactivar"
        destructive
        onConfirm={handleDeactivate}
      />
    </div>
  );
}
