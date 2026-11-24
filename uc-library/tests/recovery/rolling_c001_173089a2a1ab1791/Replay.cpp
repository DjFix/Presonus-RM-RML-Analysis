#include "presonus/avb/protocol.hpp"
#include "presonus/avb/receive_services.hpp"

#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string_view>

using Presonus::AVB::AvbListener;
using Presonus::AVB::AvbManagerBase;
using Presonus::AVB::AvbTalker;

int main() {
  AvbListener listener(27, 0x1234, 0x56, 7);
  AvbTalker talker(19, 11);
  presonus::avb::ReceiveContext context;
  AvbManagerBase manager;
  // Distinct stream arguments let both roster membership and lookup survive
  // counting. Repetition deliberately verifies CCL counts link nodes.
  auto checkMissingRole = [&] {
    try {
      manager.numFreeListeners();
      return false;
    } catch (const std::logic_error &) {
    }
    try {
      manager.numFreeTalkers();
      return false;
    } catch (const std::logic_error &) {
    }
    return true;
  };
  if (!checkMissingRole())
    return 1;
  manager.bindReceiveContext(context);
  if (!checkMissingRole() || manager.numActiveListeners() != 0)
    return 2;

  std::string_view method;
  std::string_view role;
  std::string methodArg, roleArg;
  int listeners, talkers;
  while (std::cin >> methodArg >> roleArg >> listeners >> talkers) {
    method = methodArg;
    role = roleArg;
    if ((role != "client" && role != "server") || listeners < 0 ||
        listeners > 32 || talkers < 0 || talkers > 32)
      return 3;
    manager.bindReceiveContext(context, role == "client"
                                            ? AvbManagerBase::Role::Cs18Client
                                            : AvbManagerBase::Role::RmServer);
    context.listeners.removeAll();
    context.talkers.removeAll();
    for (int i = 0; i < listeners; ++i)
      context.listeners.append(&listener);
    for (int i = 0; i < talkers; ++i)
      context.talkers.append(&talker);
    const auto originalListener = manager.findListener(27);
    const auto originalTalker = manager.findTalker(19);
    const auto originalIndex = manager.lookupNextTalkerIndex();
    int result;
    if (method == "active-listeners")
      result = manager.numActiveListeners();
    else if (method == "free-listeners")
      result = manager.numFreeListeners();
    else if (method == "free-talkers")
      result = manager.numFreeTalkers();
    else
      return 4;
    if (context.listeners.count() != listeners ||
        context.talkers.count() != talkers ||
        manager.findListener(27) != originalListener ||
        manager.findTalker(19) != originalTalker ||
        manager.lookupNextTalkerIndex() != originalIndex ||
        originalListener != (listeners ? &listener : nullptr) ||
        originalTalker != (talkers ? &talker : nullptr) ||
        originalIndex != static_cast<unsigned char>(talkers * 11))
      return 5;
    std::cout << static_cast<std::uint32_t>(result) << '\n';
  }
  manager.bindReceiveContext(context);
  return (std::cin.eof() && checkMissingRole()) ? 0 : 6;
}
