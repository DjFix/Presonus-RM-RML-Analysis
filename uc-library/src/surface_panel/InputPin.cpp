#include "presonus/surface_panel/InputPin.hpp"

namespace Presonus::Panel {
int InputPin::setup(int pin, PinStateObserver *observer) {
  pin_ = pin;
  observer_ = observer;
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
  io_->write("in", 1, 2, file_);
  io_->close(file_);
  io_->formatPath(path, sizeof(path), "/sys/class/gpio/gpio%d/value", pin_);
  file_ = io_->open(path, "r");
  if (file_ == nullptr) {
    io_->log("can't open gpio value\n");
    return -1;
  }
  io_->buffering(file_, nullptr, 2, 0);
  return 0;
}

void InputPin::read() {
  io_->rewind(file_);
  io_->flush(file_);
  const int sample = io_->get(file_) - '0';
  if (state_ == sample)
    return;
  state_ = sample;
  if (observer_ != nullptr)
    io_->notify(observer_, pin_, sample);
}

void InputPin::read_debounce() {
  io_->rewind(file_);
  io_->flush(file_);
  const int sample = io_->get(file_) - '0';
  if (last_ != sample) {
    last_ = sample;
    return;
  }
  if (state_ == sample)
    return;
  state_ = sample;
  if (observer_ != nullptr)
    io_->notify(observer_, pin_, sample);
}
} // namespace Presonus::Panel
