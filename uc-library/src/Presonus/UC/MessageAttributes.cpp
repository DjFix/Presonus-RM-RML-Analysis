#include "presonus/uc/message_attributes.hpp"

namespace Presonus::UC {
MessageAttributes::MessageAttributes(const char *id)
    : Core::Portable::Attributes(
          Core::Portable::AttributeAllocator::getDefault()) {
  if (id)
    setID(id);
}
MessageAttributes::~MessageAttributes() {}
const char *MessageAttributes::getSource() const { return getString("src"); }
const char *MessageAttributes::getURL() const { return getString("url"); }
const char *MessageAttributes::getID() const { return getString("id"); }
void MessageAttributes::setSource(const char *value) {
  set("src", value, false);
}
void MessageAttributes::setURL(const char *value) { set("url", value, false); }
void MessageAttributes::setID(const char *value) { set("id", value, false); }
} // namespace Presonus::UC
