// Base64URL <-> ArrayBuffer helpers for the WebAuthn browser API

export function b64urlToBuffer(b64url) {
  const b64 = b64url.replace(/-/g, '+').replace(/_/g, '/')
  const binary = atob(b64)
  const buf = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) buf[i] = binary.charCodeAt(i)
  return buf.buffer
}

export function bufferToB64url(buffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

// Prepare options from server (base64url strings → ArrayBuffers) for navigator.credentials.create()
export function prepareRegistrationOptions(opts) {
  return {
    ...opts,
    challenge: b64urlToBuffer(opts.challenge),
    user: { ...opts.user, id: b64urlToBuffer(opts.user.id) },
    excludeCredentials: (opts.excludeCredentials || []).map(c => ({
      ...c, id: b64urlToBuffer(c.id),
    })),
  }
}

// Prepare options from server (base64url strings → ArrayBuffers) for navigator.credentials.get()
export function prepareAuthenticationOptions(opts) {
  return {
    publicKey: {
      ...opts,
      challenge: b64urlToBuffer(opts.challenge),
      allowCredentials: (opts.allowCredentials || []).map(c => ({
        ...c, id: b64urlToBuffer(c.id),
      })),
    },
  }
}

// Convert PublicKeyCredential from browser to plain JSON-serializable object
export function serializeRegistrationCredential(credential) {
  const resp = credential.response
  return {
    id: credential.id,
    rawId: bufferToB64url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: bufferToB64url(resp.clientDataJSON),
      attestationObject: bufferToB64url(resp.attestationObject),
      transports: resp.getTransports ? resp.getTransports() : [],
    },
  }
}

export function serializeAuthenticationCredential(credential) {
  const resp = credential.response
  const result = {
    id: credential.id,
    rawId: bufferToB64url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: bufferToB64url(resp.clientDataJSON),
      authenticatorData: bufferToB64url(resp.authenticatorData),
      signature: bufferToB64url(resp.signature),
    },
  }
  if (resp.userHandle) result.response.userHandle = bufferToB64url(resp.userHandle)
  return result
}
