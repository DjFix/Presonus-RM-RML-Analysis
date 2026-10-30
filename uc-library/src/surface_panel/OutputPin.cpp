#include "presonus/surface_panel/OutputPin.hpp"

namespace Presonus::Panel {
int OutputPin::setup(int pin) {
  pin_ = pin;
  file_ = io_->open("/sys/class/gpio/export", "a");
  if (file_ == nullptr) {
    io_->log("can't open gpio export\n");
    return -1;
  }
  io_->printPin(file_, "%d", pin_);
  io_->close(file_);
  char path[256];
  io_->formatPath(path, sizeof(path), "/sys/class/gpio/gpio%d/direction", pin_);
  file_ = io_->open(path, "a");
  if (file_ == nullptr) {
    io_->log("can't open gpio direction\n");
    return -1;
  }
  io_->write("out", 1, 3, file_);
  io_->close(file_);
  io_->formatPath(path, sizeof(path), "/sys/class/gpio/gpio%d/value", pin_);
  file_ = io_->open(path, "a");
  if (file_ == nullptr) {
    io_->log("can't open gpio value\n");
    return -1;
  }
  io_->buffering(file_, nullptr, 2, 0);
  return 0;
}
void OutputPin::set(int value) {
  const int character = value == 0 ? '0' : '1';
  const int result = io_->put(character, file_);
  if (result != character) {
    const int error = io_->error();
    io_->logSet("fputc error:%d num:%d\n", result, error);
  }
  state_ = value;
}
} // namespace Presonus::Panel
