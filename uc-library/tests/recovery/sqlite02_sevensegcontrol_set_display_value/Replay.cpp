#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstdlib>
#include <iostream>
#include <string>

namespace presonus::panel_binding {
struct SevenSegControlAccess {
  static auto &bitmaps(Presonus::Panel::SevenSegControl &value) {
    return value.digitBitmaps_;
  }
};
} // namespace presonus::panel_binding

namespace {
using Presonus::Panel::SevenSegControl;
using presonus::panel_binding::SevenSegControlAccess;

class Writer : public Presonus::Panel::IPanelIO {
public:
  explicit Writer(SevenSegControl &control) : control_(control) {}

  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &message) override {
    const auto &bitmaps = SevenSegControlAccess::bitmaps(control_);
    std::cout << "write " << int(message.bytes[0]) << ' '
              << int(message.bytes[1]) << ' ' << int(message.bytes[2]) << ' '
              << bitmaps[0] << ' ' << bitmaps[1] << '\n';
    return 1;
  }
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }

private:
  SevenSegControl &control_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 7)
    return 1;
  char characters[2] = {static_cast<char>(std::stoi(argv[1])),
                        static_cast<char>(std::stoi(argv[2]))};
  bool points[2] = {std::stoi(argv[3]) != 0, std::stoi(argv[4]) != 0};
  SevenSegControl control;
  Writer writer(control);
  control.setIO(&writer);
  auto &bitmaps = SevenSegControlAccess::bitmaps(control);
  bitmaps = {static_cast<std::uint16_t>(std::stoi(argv[5])),
             static_cast<std::uint16_t>(std::stoi(argv[6]))};
  control.setValue(characters, points);
  if (static_cast<unsigned char>(characters[0]) != std::stoi(argv[1]) ||
      static_cast<unsigned char>(characters[1]) != std::stoi(argv[2]) ||
      points[0] != (std::stoi(argv[3]) != 0) ||
      points[1] != (std::stoi(argv[4]) != 0))
    return 2;
  std::cout << "final " << bitmaps[0] << ' ' << bitmaps[1] << '\n';
}
