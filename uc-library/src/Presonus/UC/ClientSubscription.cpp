#include "presonus/uc/ClientSubscription.hpp"
namespace Presonus::UC {
ClientSubscription::ClientSubscription(int identifier)
    : identifier_(identifier), word8_(0), word12_(0), byte16_(0), word20_(0) {}
} // namespace Presonus::UC
