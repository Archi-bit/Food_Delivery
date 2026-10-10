export interface Dish {
  id: number;
  name: string;
  price: string;
  photo: string | null;
  weight: number;
  is_available: boolean;
  description?: string;
}
export interface Restaurant {
  id: number;
  name: string;
  logo: string | null;
  address: string;
  description: string;
  delivery_time: number;
  min_order_price: string;
  is_open: boolean;
  avg_rating: number;
  reviews_count: number;
  categories?: { id: number; name: string; items: Dish[] }[];
}
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  delivery_address: string;
  phone_number: string;
}
export interface Cart {
  id: number;
  total_price: string;
  items: { id: number; item: Dish; quantity: number; subtotal: string }[];
}
export interface Order {
  id: number;
  restaurant: { id: number; name: string };
  delivery_address: string;
  status: string;
  status_display: string;
  created_date: string;
  total_price: string;
  order_items: {
    id: number;
    item: Dish;
    quantity: number;
    price: string;
    subtotal: string;
  }[];
}
export interface Review {
  id: number;
  user: string;
  restaurant: number;
  stars: number;
  comment: string;
}
