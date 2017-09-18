from db_controller import *
import random
from faker import Factory
import datetime
import sys

maker = Factory.create()
session = createSession(sys.argv[1])

start = datetime.datetime(year=2010, month=01, day=01)
end = datetime.datetime.now()
def random_date(start, end):
    """Generate a random datetime between `start` and `end`"""
    return start + datetime.timedelta(
        # Get a random amount of seconds between `start` and `end`
        seconds=random.randint(0, int((end - start).total_seconds())),
    )
only_author = session.query(User).filter_by(username='wcy940418').first()
languages = session.query(Language).all()
if only_author is None:
    print 'Need wcy940418 as only one author'
    exit(1)
faker_categories = [Category(name=maker.word()) for i in range(5)]
session.add_all(faker_categories)
faker_tags = [Tag(name=maker.word()) for i in range(20)]
session.add_all(faker_tags)
for i in range(10):
    post = Post(
        category=random.choice(faker_categories),
        author=only_author
    )
    post_content = PostMultiLanguage(
        title=maker.sentence(),
        content=' '.join(maker.sentences(nb=random.randint(10, 20))),
        overview=' '.join(maker.sentences(nb=random.randint(3, 5))),
        language=random.choice(languages),
        post=post,
        last_update_time=random_date(start, end)
    )
    for tag in random.sample(faker_tags, random.randint(2, 5)):
        post.tags.append(tag)
    session.add(post)
    session.add(post_content)
session.commit()
print 'generate complete'