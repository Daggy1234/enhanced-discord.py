# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING, Union, overload
from .utils import _get_as_snowflake, get
from .errors import InvalidArgument
from .partial_emoji import _EmojiTag

__all__ = (
    'WelcomeChannel',
    'WelcomeScreen',
)

if TYPE_CHECKING:
    from .types.welcome_screen import (
        WelcomeScreen as WelcomeScreenPayload,
        WelcomeScreenChannel as WelcomeScreenChannelPayload,
    )
    from .abc import Snowflake
    from .guild import Guild
    from .partial_emoji import PartialEmoji
    from .emoji import Emoji


class WelcomeChannel:
    """Represents a :class:`WelcomeScreen` welcome channel.

    .. versionadded:: 2.0

    Attributes
    -----------
    channel: :class:`abc.Snowflake`
        The guild channel that is being referenced.
    description: :class:`str`
        The description shown of the channel.
    emoji: Optional[:class:`PartialEmoji`, :class:`Emoji`, :class:`str`]
        The emoji used beside the channel description.
    """

    def __init__(self, *, channel: Snowflake, description: str, emoji: Union[PartialEmoji, Emoji, str] = None):
        self.channel = channel
        self.description = description
        self.emoji = emoji

    def __repr__(self) -> str:
        return f'<WelcomeChannel channel={self.channel!r} description={self.description!r} emoji={self.emoji!r}>'

    @classmethod
    def _from_dict(cls, *, data: WelcomeScreenChannelPayload, guild: Guild) -> WelcomeChannel:
        channel_id = _get_as_snowflake(data, 'channel_id')
        channel = guild.get_channel(channel_id)
        description = data['description']
        _emoji_id = _get_as_snowflake(data, 'emoji_id')
        _emoji_name = data['emoji_name']

        if _emoji_id:
            # custom
            emoji = get(guild.emojis, id=_emoji_id)
        else:
            # unicode or None
            emoji = _emoji_name

        return cls(channel=channel, description=description, emoji=emoji)  # type: ignore

    def to_dict(self) -> WelcomeScreenChannelPayload:
        ret: WelcomeScreenChannelPayload = {
            'channel_id': self.channel.id,
            'description': self.description,
            'emoji_id': None,
            'emoji_name': None,
        }

        if isinstance(self.emoji, _EmojiTag):
            ret['emoji_id'] = self.emoji.id  # type: ignore
            ret['emoji_name'] = self.emoji.name  # type: ignore
        else:
            # unicode or None
            ret['emoji_name'] = self.emoji

        return ret


class WelcomeScreen:
    """Represents a :class:`Guild` welcome screen.

    .. versionadded:: 2.0

    Attributes
    -----------
    description: :class:`str`
        The description shown on the welcome screen.
    welcome_channels: List[:class:`WelcomeChannel`]
        The channels shown on the welcome screen.
    """

    def __init__(self, *, data: WelcomeScreenPayload, guild: Guild):
        self._state = guild._state
        self._guild = guild
        self._store(data)

    def _store(self, data: WelcomeScreenPayload) -> None:
        self.description = data['description']
        welcome_channels = data.get('welcome_channels', [])
        self.welcome_channels = [WelcomeChannel._from_dict(data=wc, guild=self._guild) for wc in welcome_channels]

    def __repr__(self) -> str:
        return f'<WelcomeScreen description={self.description!r} welcome_channels={self.welcome_channels!r} enabled={self.enabled}>'

    @property
    def enabled(self) -> bool:
        """:class:`bool`: Whether the welcome screen is displayed.

        This is equivalent to checking if ``WELCOME_SCREEN_ENABLED``
        is present in :attr:`Guild.features`.
        """
        return 'WELCOME_SCREEN_ENABLED' in self._guild.features

    @overload
    async def edit(
        self,
        *,
        description: Optional[str] = ...,
        welcome_channels: Optional[List[WelcomeChannel]] = ...,
        enabled: Optional[bool] = ...,
    ) -> None:
        ...

    @overload
    async def edit(self) -> None:
        ...

    async def edit(self, **kwargs):
        """|coro|

        Edit the welcome screen.

        You must have the :attr:`~Permissions.manage_guild` permission in the
        guild to do this.

        Usage: ::

            rules_channel = guild.get_channel(12345678)
            announcements_channel = guild.get_channel(87654321)

            custom_emoji = utils.get(guild.emojis, name='loudspeaker')

            await welcome_screen.edit(
                description='This is a very cool community server!',
                welcome_channels=[
                    WelcomeChannel(channel=rules_channel, description='Read the rules!', emoji='👨‍🏫'),
                    WelcomeChannel(channel=announcements_channel, description='Watch out for announcements!', emoji=custom_emoji),
                ]
            )

        .. note::

            Welcome channels can only accept custom emojis if :attr:`~Guild.premium_tier` is level 2 or above.

        Parameters
        ------------
        description: Optional[:class:`str`]
            The template's description.
        welcome_channels: Optional[List[:class:`WelcomeChannel`]]
            The welcome channels, in their respective order.
        enabled: Optional[:class:`bool`]
            Whether the welcome screen should be displayed.

        Raises
        -------
        HTTPException
            Editing the welcome screen failed failed.
        Forbidden
            You don't have permissions to edit the welcome screen.
        NotFound
            This welcome screen does not exist.
        """
        try:
            welcome_channels = kwargs['welcome_channels']
        except KeyError:
            pass
        else:
            welcome_channels_serialised = []
            for wc in welcome_channels:
                if not isinstance(wc, WelcomeChannel):
                    raise InvalidArgument('welcome_channels parameter must be a list of WelcomeChannel')
                welcome_channels_serialised.append(wc.to_dict())
            kwargs['welcome_channels'] = welcome_channels_serialised

        if kwargs:
            data = await self._state.http.edit_welcome_screen(self._guild.id, kwargs)
            self._store(data)
