#include "presonus/uc/client_typed_origins.hpp"
#include <utility>
namespace presonus::uc {
ClientTypedOrigins::Binding::Binding(Binding &&other) noexcept
    : state_(std::move(other.state_)), header_(other.header_),
      serial_(other.serial_) {
  other.header_ = nullptr;
  other.serial_ = 0;
}
ClientTypedOrigins::Binding &
ClientTypedOrigins::Binding::operator=(Binding &&other) noexcept {
  if (this != &other) {
    reset();
    state_ = std::move(other.state_);
    header_ = other.header_;
    serial_ = other.serial_;
    other.header_ = nullptr;
    other.serial_ = 0;
  }
  return *this;
}
ClientTypedOrigins::Binding::~Binding() { reset(); }
void ClientTypedOrigins::Binding::reset() {
  if (auto s = state_.lock()) {
    Record r;
    if (s->records.get(r, header_) && r.serial == serial_)
      s->records.remove(header_);
  }
  state_.reset();
  header_ = nullptr;
  serial_ = 0;
}
ClientTypedOrigins::Binding::operator bool() const {
  auto s = state_.lock();
  Record r;
  return s && header_ && s->records.get(r, header_) && r.serial == serial_ &&
         header_->type == r.tag;
}
ClientTypedOrigins::Binding
ClientTypedOrigins::bindRaw(const Presonus::UC::Event &header,
                            Payload payload) {
  Record previous;
  if (state_->records.get(previous, &header))
    return {};
  if (++state_->next == 0)
    ++state_->next;
  Record r{payload, header.type, state_->next};
  state_->records.add(&header, r);
  return Binding(state_, &header, r.serial);
}
ClientTypedOrigins::Binding
ClientTypedOrigins::bind(const Presonus::UC::TimeCodeEvent &v) {
  return v.header.type == 21571 ? bindRaw(v.header, &v) : Binding{};
}
ClientTypedOrigins::Binding
ClientTypedOrigins::bind(const Presonus::UC::MessageEvent &v) {
  switch (v.header.type) {
  case 19021:
  case 21826:
  case 23106:
  case 23117:
    return bindRaw(v.header, &v);
  default:
    return {};
  }
}
ClientTypedOrigins::Binding
ClientTypedOrigins::bind(const Presonus::UC::BinaryEvent &v) {
  return v.header.type == 16975 ? bindRaw(v.header, &v) : Binding{};
}
ClientTypedOrigins::Binding
ClientTypedOrigins::bind(const Presonus::UC::DebugEvent &v) {
  return v.header.type == 17474 ? bindRaw(v.header, &v) : Binding{};
}
} // namespace presonus::uc
