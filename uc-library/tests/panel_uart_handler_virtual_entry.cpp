#include "core/portable/coretypeinfo.h"
extern "C" void uart_handler_virtual_destroy(Core::Portable::TypedObject *p) {
  p->~TypedObject();
}
extern "C" void uart_handler_virtual_delete(Core::Portable::TypedObject *p) {
  delete p;
}
