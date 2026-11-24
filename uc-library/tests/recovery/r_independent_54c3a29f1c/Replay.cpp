#include "presonus/panel/uart_message_handler.hpp"
#include "presonus/surface/DisplayManager.hpp"
#include <iostream>

namespace {
class TouchObserver final : public Presonus::UARTMessageHandler {
public:
  Presonus::TouchInputEvent event{-1, -2, -3, -4};
  unsigned callbacks = 0;

  void handleTouchscreen(Touchscreen_Type &message) override {
    ++callbacks;
    event.fromMsg(message);
  }
};
} // namespace

int main() {
  unsigned tag, x, y, packed;
  while (std::cin >> tag >> x >> y >> packed) {
    Uart_Msg_Type message{
        {static_cast<unsigned char>(tag), static_cast<unsigned char>(x),
         static_cast<unsigned char>(y), static_cast<unsigned char>(packed)}};
    const auto original = message.bytes;
    TouchObserver observer;
    const bool dispatched = tag == 'U' || tag == 'z' || tag == 'T';

    if (dispatched) {
      observer.processMsg(message, 0);
    } else {
      observer.event.fromMsg(reinterpret_cast<Touchscreen_Type &>(message));
    }

    const auto &event = observer.event;
    if (message.bytes != original || observer.callbacks != unsigned(dispatched))
      return 1;
    std::cout << event.type << ' ' << event.screen << ' ' << event.x << ' '
              << event.y << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
