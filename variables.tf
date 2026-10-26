variable "postgres_user" {
  type    = string
  default = "weebit_srvc_acc"
}

variable "postgres_password" {
  type      = string
  sensitive = true
  default   = "notverysecret"
}

variable "postgres_db" {
  type    = string
  default = "weebit_db"
}

variable "postgres_port" {
  type    = number
  default = 5432
}

variable "redis_port" {
  type    = number
  default = 6379
}
