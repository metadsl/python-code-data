def test_connect_request():
    flush_channels()
    msg = KC.session.msg('connect_request')
    KC.shell_channel.send(msg)
    return msg['header']['msg_id']

    msg_id = KC.kernel_info()
    reply = get_reply(KC, msg_id, TIMEOUT)