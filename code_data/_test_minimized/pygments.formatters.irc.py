def ircformat(color, text):
    if len(color) < 1:
        return text
    add = sub = ''
    if '_' in color: # italic
        add += '\x1D'
        sub = '\x1D' + sub
        color = color.strip('_')
    if '*' in color: # bold
        add += '\x02'
        sub = '\x02' + sub
        color = color.strip('*')
    # underline (\x1F) not supported
    # backgrounds (\x03FF,BB) not supported
    if len(color) > 0: # actual color - may have issues with ircformat("red", "blah")+"10" type stuff
        add += '\x03' + str(IRC_COLOR_MAP[color]).zfill(2)
        sub = '\x03' + sub
    return add + text + sub
    return '<'+add+'>'+text+'</'+sub+'>'