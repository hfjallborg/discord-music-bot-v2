import pafy
import youtubesearchpython


def get_audio(url):
    """Retrieves a :class:`pafy.Stream` from a YouTube url.

    :param url: URL of youtube video, can also be the 11 char
        video id.
    :type url: str
    """
    audio = pafy.new(url).getbestaudio()
    return audio

def find_video(search_term):
    """Attempts to find a YouTube video id from search term(s).

    :param search_term: Words/keywords/phrases to use when
        searching for video. This is what you would
        enter into YouTube's search bar.
    :type search_term: str
    """
    yt_search = youtubesearchpython.VideosSearch(search_term, limit=1)
    result = yt_search.result()["result"][0]
    result = {
        "title": result["title"],
        "url": result["link"]
    }
    return result
