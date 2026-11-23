#include "presonus/panel/AlertBook.hpp"
#include "core/system/coredebug.h"
#include "core/system/coretime.h"
#include "presonus/panel/Book.hpp"

namespace Presonus::Panel {
namespace {
using Core::Portable::ParamInfo;

constexpr ParamInfo alertParameters[] = {
    {ParamInfo::kString, 100, "title", 0, 0, 0, 0, 0, 0, nullptr, nullptr,
     nullptr, "Alert title", nullptr},
    {ParamInfo::kString, 101, "message1", 0, 0, 0, 0, 0, 0, nullptr, nullptr,
     nullptr, "Alert message", nullptr},
    {ParamInfo::kString, 102, "message2", 0, 0, 0, 0, 0, 0, nullptr, nullptr,
     nullptr, "Alert message 2", nullptr},
};
} // namespace

struct AlertBook::OwnedState {
  explicit OwnedState(int initialValue)
      : book(initialValue), parameters("alert") {
    parameters.addParameters(alertParameters, 3, false);
  }

  Book book;
  Core::Portable::Component parameters;
};

AlertBook::AlertBook(int initialValue)
    : owned_(std::make_shared<OwnedState>(initialValue)),
      parameters_(owned_->parameters) {}
AlertBook::~AlertBook() = default;

const Book *AlertBook::portableOwnedBook() const {
  return owned_ ? &owned_->book : nullptr;
}

void AlertBook::setParamString(const char *text, int tag) {
  if (auto *p = parameters_.getParameterByTag(tag))
    if (auto *string = Core::Portable::StringParam::cast(p))
      string->fromString(text, false);
}
void AlertBook::setup(Page *page, Core::Portable::Parameter *selection,
                      const char *first, const char *second, const char *third,
                      int mode) {
  state_.mode = mode;
  state_.page = page;
  state_.selection = selection;
  if (selection) {
    selection->setValue(1.f, false);
    selection->addObserver(&parameters_);
  }
  setParamString(first, 100);
  setParamString(second, 101);
  setParamString(third, 102);
  // Pinned Linux SystemClock is signed nanoseconds; exact native truncation.
  state_.startedMilliseconds = Core::SystemClock::getTime() / 1000000;
}
void AlertBook::deactivated() {
  Core::DebugPrint("AlertBook::deactivated\n");
  state_.mode = 0;
  if (state_.selection) {
    state_.selection->removeObserver(&parameters_);
    state_.selection->setValue(0.f, false);
    state_.selection = nullptr;
  }
  setParamString("", 100);
  setParamString("", 101);
  setParamString("", 102);
}

void AlertBook::pageup() {}

void AlertBook::pagedown() {}

void AlertBook::next() {}

void AlertBook::previous() {}
} // namespace Presonus::Panel
