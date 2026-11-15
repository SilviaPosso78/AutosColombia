export interface ClienteCrear {
  documento: string;
  nombre: string;
  telefono: string;
  correo: string | null;
}
export type ClienteActualizar = Partial<ClienteCrear>;
export interface Cliente extends ClienteCrear {
  id: number;
}
export interface ClientesPagina {
  items: Cliente[];
  total: number;
  offset: number;
  limit: number;
}
