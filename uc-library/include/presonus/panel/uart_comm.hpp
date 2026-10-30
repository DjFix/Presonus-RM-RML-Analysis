#pragma once
#include "presonus/panel/protocol_comm.hpp"
#include <cstdint>
#include <memory>
#include <termios.h>

namespace presonus::panel {
// Independent source-port boundary. The production provider calls the actual
// POSIX APIs and existing CCL monotonic clock gateway; tests supply contracts.
class UartServices {
public:
  virtual ~UartServices() = default;
  virtual int openFile(const char *path, int flags) = 0;
  virtual int closeFile(int descriptor) = 0;
  virtual int readFile(int descriptor, void *buffer, std::uint32_t size) = 0;
  virtual int writeFile(int descriptor, const void *buffer,
                        std::uint32_t size) = 0;
  virtual int exclusive(int descriptor, unsigned long request) = 0;
  virtual int getAttributes(int descriptor, termios &attributes) = 0;
  virtual void makeRaw(termios &attributes) = 0;
  virtual int setSpeed(termios &attributes, speed_t speed) = 0;
  virtual int setAttributes(int descriptor, int action,
                            const termios &attributes) = 0;
  virtual int setFlags(int descriptor, int command, int flags) = 0;
  virtual void printError(const char *prefix) = 0;
  virtual std::int64_t rawTicks() = 0;
};
UartServices &systemUartServices();
struct UartCommAccess;
} // namespace presonus::panel

namespace Presonus::Panel {
// Original application hierarchy/virtual slot order comes from RTTI/vtables.
// Storage is an independent source port, not an original ARM object layout.
class UARTComm : public ProtocolComm {
public:
  UARTComm();
  ~UARTComm() override;
  UARTComm(const UARTComm &) = delete;
  UARTComm &operator=(const UARTComm &) = delete;
  // All ordinary return spellings are portable choices, declaration-pending.
  int open(const char *path) override;
  void close() override;
  int enableHISpeed(bool enabled) override;
  int write(const char *buffer, int size) override;
  int read(char *buffer, int size) override;
  unsigned char getNextChar(int timeout);

private:
  int descriptor_;
  presonus::panel::UartServices *services_;
  // Independent retained provider binding, not an original ARM member.
  std::shared_ptr<presonus::panel::UartServices> ownedServices_;
  friend struct presonus::panel::UartCommAccess;
};
} // namespace Presonus::Panel

namespace presonus::panel {
// Independent fixture/setup access; configure before use, never concurrently.
struct UartCommAccess {
  // Production binding owns its provider beyond the Manager/configuration.
  // Called while UART users are quiescent; closes via old provider first.
  static void ownedServices(Presonus::Panel::UARTComm &uart,
                            std::shared_ptr<UartServices> services);
  static void services(Presonus::Panel::UARTComm &uart,
                       UartServices &services) {
    if (uart.services_ != &services)
      uart.ownedServices_.reset();
    uart.services_ = &services;
  }
  static int descriptor(const Presonus::Panel::UARTComm &uart) {
    return uart.descriptor_;
  }
  static void descriptor(Presonus::Panel::UARTComm &uart, int value) {
    uart.descriptor_ = value;
  }
};
} // namespace presonus::panel
