#include "presonus/MappingTable.hpp"
namespace Presonus {
bool MappingTable::extractPageName(const char *input,
                                   Core::CStringBuffer<32> &page,
                                   Core::CStringBuffer<32> &parameter) {
  // Native guarded locals initialize the prefix first, then its length.
  static const Core::ConstString pagePrefix("page:");
  static const int prefixLength = pagePrefix.length();
  const char *text = input ? input : "";
  if (std::strstr(text, pagePrefix.str()) != text)
    return false;
  const char *dot = std::strchr(text, '.');
  if (!dot || dot - text <= 0)
    return false;
  // Preserve native operation order, including bounded copy before truncation.
  page = text + prefixLength;
  page.truncate(static_cast<int>(dot - text) - prefixLength);
  parameter = dot + 1;
  return true;
}
} // namespace Presonus
