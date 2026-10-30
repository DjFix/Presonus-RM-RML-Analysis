#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/BitmapDrawing.hpp"
namespace Presonus::Panel {
void BitmapDisplay::setPort(IPanelIO *port) { port_ = port; }
void BitmapDisplay::update(bool force) {
  if (port_ == nullptr)
    return;
  Core::Threads::ScopedLock guard(textLock_);
  static unsigned char firstIn = 1; // Original local-static identity;
                                    // declaration spelling remains provisional.
  if (firstIn) {
    firstIn = 0;
    force = true;
  }
  if (!force && !textDirty_)
    return;
  textDirty_ = false;
  int expected = -1;
  bool sent = false;
  for (int offset = 0; offset <= 1535;) {
    if (!force && bitmap_[offset] == lastSent_[offset]) {
      ++offset;
      continue;
    }
    if (expected != offset) {
      Uart_Msg_Type address{{0x62, 4, static_cast<std::uint8_t>(offset),
                             static_cast<std::uint8_t>(offset >> 8)}};
      port_->writeMsg(address);
    }
    Uart_Msg_Type data{
        {0x6c, bitmap_[offset], bitmap_[offset + 1], bitmap_[offset + 2]}};
    for (int i = 0; i < 3; ++i)
      lastSent_[offset + i] = bitmap_[offset + i];
    port_->writeMsg(data);
    offset += 3;
    expected = offset;
    sent = true;
  }
  if (sent) {
    Uart_Msg_Type end{{0x62, 0, 0, 0}};
    port_->writeMsg(end);
  }
}
} // namespace Presonus::Panel
