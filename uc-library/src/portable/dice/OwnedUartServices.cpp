#include "presonus/panel/uart_comm.hpp"
#include <stdexcept>
#include <utility>
namespace presonus::panel {
void UartCommAccess::ownedServices(Presonus::Panel::UARTComm &uart,
                                   std::shared_ptr<UartServices> services) {
  if (!services)
    throw std::invalid_argument("Owned UART services are required");
  if (uart.services_ != services.get())
    uart.close(); // Old provider is alive during descriptor close.
  uart.ownedServices_ = std::move(services);
  uart.services_ = uart.ownedServices_.get();
}
} // namespace presonus::panel
