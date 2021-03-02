#! /usr/bin/env python
"""Public-key encryption and signature algorithms.

Public-key encryption uses two different keys, one for encryption and
one for decryption.  The encryption key can be made public, and the
decryption key is kept private.  Many public-key algorithms can also
be used to sign messages, and some can *only* be used for signatures.

Crypto.PublicKey.DSA      Digital Signature Algorithm. (Signature only)
Crypto.PublicKey.ElGamal  (Signing and encryption)
Crypto.PublicKey.RSA      (Signing, encryption, and blinding)
Crypto.PublicKey.qNEW     (Signature only)

"""

__all__ = ['RSA', 'DSA', 'ElGamal', 'qNEW', 'pubkey']
__revision__ = "$Id: __init__.py,v 1.2 2006/07/29 02:52:50 phil Exp $"

