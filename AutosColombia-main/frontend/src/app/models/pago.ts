export type EstadoMensualidad =
  'SIN_MENSUALIDAD' | 'PROGRAMADA' | 'VIGENTE' | 'POR_VENCER' | 'VENCIDA';

export interface Mensualidad {
  vehiculo_id: number;
  placa: string;
  tipo: string;
  tarifa_mensual: string;
  cliente_id: number | null;
  cliente_nombre: string | null;
  telefono: string | null;
  pago_id: number | null;
  inicio: string | null;
  fin: string | null;
  dias_restantes: number | null;
  estado: EstadoMensualidad;
}

export interface PagoCrear {
  solicitud_id: string;
  placa: string;
  operador_id: number;
  valor: string;
  fecha_pago: string;
  inicio: string;
  fin: string;
}

export interface Pago {
  id: number;
  solicitud_id: string;
  vehiculo_id: number;
  cliente_id: number;
  operador_id: number;
  tipo_vehiculo: string;
  valor: string;
  fecha_pago: string;
  inicio: string;
  fin: string;
  creado_en: string;
}

export interface PagoHistorial extends Pago {
  placa: string;
  cliente_nombre: string;
  operador_nombre: string;
}

export interface Aviso {
  id: number;
  pago_id: number;
  placa: string;
  cliente_nombre: string;
  telefono: string | null;
  programado_para: string;
  fin: string;
  dias_antes: number;
  estado: string;
  detalle: string | null;
  enviado_en: string | null;
  texto: string;
}

export interface ConfiguracionAvisos {
  habilitado: boolean;
  configurado: boolean;
  faltantes: string[];
  dias_anticipacion: number;
}

export interface Pagina<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}
